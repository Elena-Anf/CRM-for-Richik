import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

templates = Jinja2Templates(directory="app/templates")

from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.pet import Pet
from app.models.master import Master
from app.models.service import Service
from app.schemas.appointment import AppointmentCreate, AppointmentResponse, AppointmentStatusUpdate, AppointmentReschedule, AppointmentUpdate
from app.services.google_calendar import create_event, update_event, delete_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    master_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.pet),
            joinedload(Appointment.master),
            joinedload(Appointment.service),
        )
    )

    if date_from:
        dt_from = datetime.datetime.fromisoformat(date_from)
        stmt = stmt.where(Appointment.start_time >= dt_from)
    if date_to:
        dt_to = datetime.datetime.fromisoformat(date_to)
        stmt = stmt.where(Appointment.start_time <= dt_to)
    if master_id:
        stmt = stmt.where(Appointment.master_id == master_id)
    if status:
        stmt = stmt.where(Appointment.status == status)

    stmt = stmt.order_by(Appointment.start_time.asc())
    result = await db.execute(stmt)
    appointments = result.unique().scalars().all()

    return [
        AppointmentResponse(
            id=a.id,
            client_name=a.client.name,
            client_phone=a.client.phone,
            pet_name=a.pet.name,
            pet_species=a.pet.species,
            pet_breed=a.pet.breed if a.pet else "",
            master_id=a.master_id,
            master_name=a.master.name,
            service_id=a.service_id,
            service_name=a.service.name,
            start_time=a.start_time,
            end_time=a.end_time,
            status=a.status,
            price=a.price or a.service.price,
            cost_price=a.cost_price or a.service.cost_price,
            master_earnings=a.master_earnings,
            notes=a.notes or "",
            google_event_id=a.google_event_id,
        )
        for a in appointments
    ]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.pet),
            joinedload(Appointment.master),
            joinedload(Appointment.service),
        )
        .where(Appointment.id == appointment_id)
    )
    result = await db.execute(stmt)
    a = result.unique().scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Appointment not found")

    return AppointmentResponse(
        id=a.id,
        client_name=a.client.name,
        client_phone=a.client.phone,
        pet_name=a.pet.name,
        pet_species=a.pet.species,
        pet_breed=a.pet.breed if a.pet else "",
        master_id=a.master_id,
        master_name=a.master.name,
        service_id=a.service_id,
        service_name=a.service.name,
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status,
        price=a.price or a.service.price,
        cost_price=a.cost_price or a.service.cost_price,
        master_earnings=a.master_earnings,
        notes=a.notes or "",
        google_event_id=a.google_event_id,
    )


@router.post("/", response_model=AppointmentResponse, status_code=201)
async def create_appointment(data: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    service = await db.get(Service, data.service_id)
    if not service:
        raise HTTPException(404, "Service not found")

    master = await db.get(Master, data.master_id)
    if not master or not master.is_active:
        raise HTTPException(404, "Master not found")

    duration = data.duration_minutes or service.duration_minutes
    end_time = data.start_time + datetime.timedelta(minutes=duration)

    stmt = select(Client).where(Client.phone == data.client_phone)
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        client = Client(
            name=data.client_name,
            phone=data.client_phone,
            email=data.client_email or "",
        )
        db.add(client)
        await db.flush()

    pet = Pet(
        client_id=client.id,
        name=data.pet_name,
        species=data.pet_species,
        breed=data.pet_breed or "",
    )
    db.add(pet)
    await db.flush()

    final_price = data.price if data.price is not None else service.price
    final_cost = data.cost_price if data.cost_price is not None else service.cost_price
    master_earnings = round(final_price * master.commission_percent / 100, 2)

    appointment = Appointment(
        client_id=client.id,
        pet_id=pet.id,
        master_id=data.master_id,
        service_id=data.service_id,
        start_time=data.start_time,
        end_time=end_time,
        status="pending",
        price=final_price,
        cost_price=final_cost,
        master_earnings=master_earnings,
        notes=data.notes or "",
    )
    db.add(appointment)
    await db.flush()

    appointment.google_event_id = await create_event(db, appointment)
    await db.commit()
    await db.refresh(appointment)

    return AppointmentResponse(
        id=appointment.id,
        client_name=client.name,
        client_phone=client.phone,
        pet_name=pet.name,
        pet_species=pet.species,
        pet_breed=pet.breed,
        master_id=data.master_id,
        master_name=master.name,
        service_id=data.service_id,
        service_name=service.name,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        status=appointment.status,
        price=appointment.price,
        cost_price=appointment.cost_price,
        master_earnings=appointment.master_earnings,
        notes=appointment.notes or "",
        google_event_id=appointment.google_event_id,
    )


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: int,
    data: AppointmentStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.pet),
            joinedload(Appointment.master),
            joinedload(Appointment.service),
        )
        .where(Appointment.id == appointment_id)
    )
    result = await db.execute(stmt)
    a = result.unique().scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Appointment not found")

    a.status = data.status

    if data.status == "completed" and not a.master_earnings:
        a.master_earnings = round((a.price or a.service.price) * a.master.commission_percent / 100, 2)
        a.cost_price = a.cost_price or a.service.cost_price

    if data.status == "cancelled" and a.google_event_id:
        await delete_event(db, a)
        a.google_event_id = None

    await db.commit()
    await db.refresh(a)

    return AppointmentResponse(
        id=a.id,
        client_name=a.client.name,
        client_phone=a.client.phone,
        pet_name=a.pet.name,
        pet_species=a.pet.species,
        pet_breed=a.pet.breed if a.pet else "",
        master_id=a.master_id,
        master_name=a.master.name,
        service_id=a.service_id,
        service_name=a.service.name,
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status,
        price=a.price or a.service.price,
        cost_price=a.cost_price or a.service.cost_price,
        master_earnings=a.master_earnings,
        notes=a.notes or "",
        google_event_id=a.google_event_id,
    )


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: int,
    data: AppointmentReschedule,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.pet),
            joinedload(Appointment.master),
            joinedload(Appointment.service),
        )
        .where(Appointment.id == appointment_id)
    )
    result = await db.execute(stmt)
    a = result.unique().scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Appointment not found")

    duration = (a.end_time - a.start_time).total_seconds() / 60
    a.start_time = data.start_time
    a.end_time = data.start_time + datetime.timedelta(minutes=duration)

    if a.google_event_id:
        await update_event(db, a)
    else:
        a.google_event_id = await create_event(db, a)

    await db.commit()
    await db.refresh(a)

    return AppointmentResponse(
        id=a.id,
        client_name=a.client.name,
        client_phone=a.client.phone,
        pet_name=a.pet.name,
        pet_species=a.pet.species,
        pet_breed=a.pet.breed if a.pet else "",
        master_id=a.master_id,
        master_name=a.master.name,
        service_id=a.service_id,
        service_name=a.service.name,
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status,
        price=a.price or a.service.price,
        cost_price=a.cost_price or a.service.cost_price,
        master_earnings=a.master_earnings,
        notes=a.notes or "",
        google_event_id=a.google_event_id,
    )


def _calc(apps: list) -> dict:
    revenue = round(sum(a.price or 0 for a in apps), 2)
    cost = round(sum(a.cost_price or a.service.cost_price for a in apps), 2)
    earnings = round(sum(a.master_earnings or 0 for a in apps), 2)
    return {
        "revenue": revenue,
        "cost": cost,
        "earnings": earnings,
        "profit": round(revenue - cost - earnings, 2),
        "count": len(apps),
    }


@router.patch("/{appointment_id}/edit", response_model=AppointmentResponse)
async def edit_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.pet),
            joinedload(Appointment.master),
            joinedload(Appointment.service),
        )
        .where(Appointment.id == appointment_id)
    )
    result = await db.execute(stmt)
    a = result.unique().scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Appointment not found")

    old_duration = (a.end_time - a.start_time).total_seconds() / 60

    if data.client_name is not None:
        a.client.name = data.client_name
    if data.client_phone is not None:
        a.client.phone = data.client_phone
    if data.pet_name is not None:
        a.pet.name = data.pet_name
    if data.pet_species is not None:
        a.pet.species = data.pet_species
    if data.pet_breed is not None:
        a.pet.breed = data.pet_breed
    if data.start_time is not None:
        a.start_time = data.start_time
    if data.duration_minutes is not None:
        a.end_time = a.start_time + datetime.timedelta(minutes=data.duration_minutes)
    elif data.start_time is not None:
        a.end_time = a.start_time + datetime.timedelta(minutes=old_duration)
    if data.master_id is not None and data.master_id != a.master_id:
        if a.google_event_id:
            await delete_event(db, a)
            a.google_event_id = None
        a.master_id = data.master_id
    if data.service_id is not None:
        new_service = await db.get(Service, data.service_id)
        if new_service:
            a.service_id = data.service_id
            price = data.price if data.price is not None else new_service.price
            a.price = price
            master = await db.get(Master, a.master_id)
            if master:
                a.master_earnings = round(price * master.commission_percent / 100, 2)
    if data.status is not None:
        a.status = data.status
        if data.status in ("completed", "confirmed") and not a.master_earnings:
            master = await db.get(Master, a.master_id)
            if master:
                a.master_earnings = round((a.price or a.service.price) * master.commission_percent / 100, 2)
        if data.status == "cancelled" and a.google_event_id:
            await delete_event(db, a)
            a.google_event_id = None
    if data.notes is not None:
        a.notes = data.notes
    if data.cost_price is not None:
        a.cost_price = data.cost_price
    if data.price is not None:
        a.price = data.price
        master = await db.get(Master, a.master_id)
        if master:
            a.master_earnings = round(data.price * master.commission_percent / 100, 2)

    # Sync Google Calendar event after all field updates
    if a.status != "cancelled":
        if a.google_event_id:
            await update_event(db, a)
        else:
            a.google_event_id = await create_event(db, a)

    await db.commit()
    await db.refresh(a)
    await db.refresh(a.client)
    await db.refresh(a.pet)

    return AppointmentResponse(
        id=a.id,
        client_name=a.client.name,
        client_phone=a.client.phone,
        pet_name=a.pet.name,
        pet_species=a.pet.species,
        pet_breed=a.pet.breed if a.pet else "",
        master_id=a.master_id,
        master_name=a.master.name,
        service_id=a.service_id,
        service_name=a.service.name,
        start_time=a.start_time,
        end_time=a.end_time,
        status=a.status,
        price=a.price or a.service.price,
        cost_price=a.cost_price or a.service.cost_price,
        master_earnings=a.master_earnings,
        notes=a.notes or "",
        google_event_id=a.google_event_id,
    )


@router.get("/finance/stats")
async def finance_stats(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    master_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Appointment).options(joinedload(Appointment.service))

    conditions = []
    if date_from:
        conditions.append(Appointment.start_time >= datetime.datetime.fromisoformat(date_from))
    if date_to:
        conditions.append(Appointment.start_time <= datetime.datetime.fromisoformat(date_to))
    if master_id:
        conditions.append(Appointment.master_id == master_id)

    if conditions:
        stmt = stmt.where(*conditions)

    result = await db.execute(stmt)
    all_apps = result.unique().scalars().all()

    pending_apps = [a for a in all_apps if a.status in ("pending", "confirmed")]
    paid_apps = [a for a in all_apps if a.status == "completed"]
    cancelled_apps = [a for a in all_apps if a.status == "cancelled"]

    expected = _calc(pending_apps)
    paid = _calc(paid_apps)
    cancelled = _calc(cancelled_apps)

    total_revenue = expected["revenue"] + paid["revenue"]
    total_cost = expected["cost"] + paid["cost"]
    total_earnings = expected["earnings"] + paid["earnings"]
    total_profit = expected["profit"] + paid["profit"]

    context = {
        "expected": expected,
        "paid": paid,
        "cancelled": cancelled,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "total_master_earnings": total_earnings,
        "total_profit": total_profit,
        "appointments_count": len(all_apps),
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "components/finance_stats.html", context)

    return context


@router.delete("/{appointment_id}", status_code=204)
async def delete_appointment(appointment_id: int, db: AsyncSession = Depends(get_db)):
    a = await db.get(Appointment, appointment_id)
    if not a:
        raise HTTPException(404, "Appointment not found")

    if a.google_event_id:
        await delete_event(db, a)

    await db.delete(a)
    await db.commit()
