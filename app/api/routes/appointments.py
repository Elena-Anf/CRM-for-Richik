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
from app.services.google_calendar import create_event, update_event, delete_event, _get_service

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


@router.post("/sync-from-calendar")
async def sync_from_calendar(db: AsyncSession = Depends(get_db)):
    stats = {"created": 0, "cancelled": 0, "updated": 0, "errors": []}

    masters = await db.execute(
        select(Master).where(
            Master.is_active == True,
            Master.google_calendar_id != None,
            Master.google_calendar_id != "",
        )
    )
    masters = masters.scalars().all()
    if not masters:
        return {"message": "Нет мастеров с подключённым календарём", "stats": stats}

    all_appts = await db.execute(
        select(Appointment)
        .options(
            joinedload(Appointment.client),
            joinedload(Appointment.pet),
            joinedload(Appointment.service),
            joinedload(Appointment.master),
        )
    )
    all_appts = all_appts.unique().scalars().all()
    if not all_appts:
        return {"message": "Нет записей для сверки", "stats": stats}

    raw_min = min(a.start_time for a in all_appts) - datetime.timedelta(days=3)
    raw_max = max(a.start_time for a in all_appts) + datetime.timedelta(days=3)

    logger.info("SYNC date range raw: %s — %s", raw_min, raw_max)

    service = _get_service()
    if not service:
        raise HTTPException(400, "Google Calendar service not configured")

    all_events = []
    for m in masters:
        try:
            tz_msk = datetime.timezone(datetime.timedelta(hours=3))
            if raw_min.tzinfo is None:
                time_min = raw_min.replace(tzinfo=tz_msk)
            else:
                time_min = raw_min
            if raw_max.tzinfo is None:
                time_max = raw_max.replace(tzinfo=tz_msk)
            else:
                time_max = raw_max

            time_min_str = time_min.isoformat()
            time_max_str = time_max.isoformat()
            logger.info("SYNC fetching master=%s calendar=%s from=%s to=%s",
                        m.name, m.google_calendar_id[:20], time_min_str, time_max_str)

            events_result = service.events().list(
                calendarId=m.google_calendar_id,
                timeMin=time_min_str,
                timeMax=time_max_str,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            items = events_result.get("items", [])
            logger.info("SYNC master=%s got %d events", m.name, len(items))
            for ev in items:
                ev["_master_id"] = m.id
                logger.info("SYNC event id=%s summary=%s start=%s",
                            ev.get("id","")[:12], ev.get("summary",""),
                            ev.get("start",{}).get("dateTime",""))
            all_events.extend(items)
        except Exception as e:
            logger.error("SYNC error for master %s: %s", m.name, e)
            stats["errors"].append(f"Master {m.name}: {e}")

    if not all_events:
        return {"message": "Нет событий в календарях за выбранный период", "stats": stats}

    # Build lookup: by google_event_id first (exact), then by composite key
    appts_by_event_id = {}
    grouped_appts = {}
    for a in all_appts:
        if a.status == "cancelled":
            continue
        if a.google_event_id:
            appts_by_event_id[a.google_event_id] = a
        key = _appointment_key(a)
        grouped_appts.setdefault(a.master_id, {}).setdefault(key, []).append(a)

    for mid, keys in grouped_appts.items():
        logger.info("SYNC master %s CRM keys: %s", mid, list(keys.keys()))

    matched_crm_ids = set()

    for ev in all_events:
        parsed = _parse_event(ev)
        if not parsed:
            continue

        master_id = ev["_master_id"]
        start = _parse_event_time(ev.get("start", {}).get("dateTime", ""))
        end = _parse_event_time(ev.get("end", {}).get("dateTime", ""))
        if not start or not end:
            continue
        duration_minutes = int((end - start).total_seconds() / 60)

        # Match by google_event_id first (exact match)
        match = appts_by_event_id.get(ev.get("id"))
        if not match:
            # Fallback to composite key matching
            ev_key = _make_key(parsed["client_name"], parsed["client_phone"], parsed["pet_name"], parsed["pet_breed"])
            ev_key_no_breed = _make_key(parsed["client_name"], parsed["client_phone"], parsed["pet_name"], "")

            logger.info("SYNC event[%s] master=%s key=%s phone=%s pet=%s breed=%s",
                        ev.get("id","")[:8], master_id, ev_key,
                        parsed.get("client_phone"), parsed.get("pet_name"), parsed.get("pet_breed"))

            candidates = grouped_appts.get(master_id, {}).get(ev_key, []) or grouped_appts.get(master_id, {}).get(ev_key_no_breed, [])

            if not candidates:
                logger.info("SYNC no match for key=%s. Available keys for master %s: %s",
                            ev_key, master_id, list(grouped_appts.get(master_id, {}).keys()))
            match = candidates[0] if candidates else None

        if match:
            a = match
            matched_crm_ids.add(a.id)
            needs_update = False

            if parsed.get("service_name"):
                svc = await _find_service(db, parsed["service_name"])
                if svc and svc.id != a.service_id:
                    a.service_id = svc.id
                    a.price = svc.price
                    master_obj = await db.get(Master, a.master_id)
                    if master_obj:
                        a.master_earnings = round(svc.price * master_obj.commission_percent / 100, 2)
                    needs_update = True

            time_diff = abs((a.start_time.replace(tzinfo=None) - start.replace(tzinfo=None)).total_seconds())
            if time_diff > 60:
                a.start_time = start
                a.end_time = start + datetime.timedelta(minutes=duration_minutes)
                needs_update = True

            if needs_update:
                if a.google_event_id:
                    await update_event(db, a)
                else:
                    a.google_event_id = ev.get("id")
                stats["updated"] += 1
        else:
            svc = None
            if parsed.get("service_name"):
                svc = await _find_service(db, parsed["service_name"])
            if not svc:
                svc = await _find_service(db, "Стрижка")
            if not svc:
                svcs = await db.execute(select(Service).where(Service.is_active == True))
                svc = svcs.scalars().first()
            if not svc:
                stats["errors"].append("Нет доступных услуг для создания записи")
                continue

            client = await db.execute(
                select(Client).where(
                    Client.name == parsed["client_name"],
                    Client.phone == parsed["client_phone"],
                )
            )
            client = client.scalar_one_or_none()
            if not client:
                client = Client(name=parsed["client_name"], phone=parsed["client_phone"])
                db.add(client)
                await db.flush()

            pets = await db.execute(
                select(Pet).where(
                    Pet.client_id == client.id,
                    Pet.name == parsed["pet_name"],
                )
            )
            pet = pets.scalars().first()
            if not pet:
                pet = Pet(
                    client_id=client.id,
                    name=parsed["pet_name"],
                    species=parsed.get("pet_species", "dog"),
                    breed=parsed["pet_breed"],
                )
                db.add(pet)
                await db.flush()

            master_obj = await db.get(Master, master_id)
            commission = master_obj.commission_percent if master_obj else 40
            master_earnings = round(svc.price * commission / 100, 2)

            appointment = Appointment(
                client_id=client.id,
                pet_id=pet.id,
                master_id=master_id,
                service_id=svc.id,
                start_time=start,
                end_time=end,
                status="pending",
                price=svc.price,
                cost_price=svc.cost_price,
                master_earnings=master_earnings,
                google_event_id=ev.get("id"),
            )
            db.add(appointment)
            stats["created"] += 1

    not_matched = [
        a for a in all_appts
        if a.status != "cancelled"
        and a.id not in matched_crm_ids
        and a.master_id in {m.id for m in masters}
    ]
    for a in not_matched:
        a.status = "cancelled"
        if a.google_event_id:
            await delete_event(db, a)
            a.google_event_id = None
        stats["cancelled"] += 1

    await db.commit()
    return {"message": "Синхронизация завершена", "stats": stats}


def _appointment_key(a: Appointment) -> str:
    name = (a.client.name or "").strip().lower()
    phone = (a.client.phone or "").strip().lower()
    pet_name = (a.pet.name or "").strip().lower()
    breed = (a.pet.breed or "").strip().lower()
    return _make_key(name, phone, pet_name, breed)


def _make_key(name: str, phone: str, pet_name: str, breed: str) -> str:
    return f"{name}|{phone}|{pet_name}|{breed}"


def _parse_event(ev: dict) -> Optional[dict]:
    desc = ev.get("description", "") or ""
    summary = ev.get("summary", "") or ""

    result = {}

    if "Клиент:" in desc:
        for line in desc.split("\n"):
            line = line.strip()
            if line.startswith("Клиент:"):
                result["client_name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Телефон:"):
                result["client_phone"] = line.split(":", 1)[1].strip()
            elif line.startswith("Питомец:"):
                pet_part = line.split(":", 1)[1].strip()
                if "(" in pet_part:
                    result["pet_name"] = pet_part.split("(")[0].strip()
                    breed_species = pet_part.split("(")[1].rstrip(")")
                    result["pet_breed"] = breed_species
                    result["pet_species"] = breed_species
                else:
                    result["pet_name"] = pet_part
            elif line.startswith("Услуга:"):
                svc_part = line.split(":", 1)[1].strip()
                if "—" in svc_part:
                    result["service_name"] = svc_part.split("—")[0].strip()
                else:
                    result["service_name"] = svc_part

    if not result.get("client_name") and "(" in summary and ")" in summary:
        parts = summary.split("(")
        if len(parts) >= 2:
            name_part = parts[-1].rstrip(")")
            result["client_name"] = name_part.strip()

    if not result.get("service_name") and "—" in summary:
        result["service_name"] = summary.split("—")[0].strip()

    if not result.get("pet_name") and "—" in summary and "(" in summary:
        between = summary.split("—", 1)[1].strip()
        if "(" in between:
            result["pet_name"] = between.split("(")[0].strip()

    if not result.get("client_name"):
        return None

    result.setdefault("client_phone", "")
    result.setdefault("pet_name", "")
    result.setdefault("pet_breed", "")
    result.setdefault("pet_species", "dog")
    result.setdefault("service_name", "")
    return result


def _parse_event_time(t_str: str) -> Optional[datetime.datetime]:
    if not t_str:
        return None
    t_str = t_str.replace("Z", "+00:00")
    for sep in ["+", "-"]:
        if sep in t_str:
            parts = t_str.rsplit(sep, 1)
            if len(parts) == 2 and ":" not in parts[1]:
                t_str = parts[0] + sep + parts[1][:2] + ":" + parts[1][2:]
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
        try:
            dt = datetime.datetime.strptime(t_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        except ValueError:
            continue
    return None


async def _find_service(db: AsyncSession, name: str) -> Optional[Service]:
    name = name.strip().lower()
    svcs = await db.execute(select(Service).where(Service.is_active == True))
    for s in svcs.scalars().all():
        if s.name.strip().lower() == name:
            return s
    for s in svcs.scalars().all():
        if name in s.name.strip().lower():
            return s
    return None
