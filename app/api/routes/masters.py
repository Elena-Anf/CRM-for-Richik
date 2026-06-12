import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.master import Master
from app.schemas.master import MasterCreate, MasterResponse

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/")
async def list_masters(request: Request, db: AsyncSession = Depends(get_db)):
    stmt = select(Master).order_by(Master.name.asc())
    result = await db.execute(stmt)
    masters = result.scalars().all()
    data = [
        MasterResponse(
            id=m.id,
            name=m.name,
            phone=m.phone,
            email=m.email,
            bio=m.bio,
            color=m.color,
            commission_percent=m.commission_percent,
            is_active=m.is_active,
            calendar_iframe=m.calendar_iframe or "",
            google_calendar_id=m.google_calendar_id or "",
        )
        for m in masters
    ]

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "components/master_row.html", {"masters": data})

    return data


@router.post("/", status_code=201)
async def create_master(request: Request, data: MasterCreate, db: AsyncSession = Depends(get_db)):
    m = Master(**data.model_dump())
    db.add(m)
    await db.commit()
    await db.refresh(m)
    result = MasterResponse(
        id=m.id,
        name=m.name,
        phone=m.phone,
        email=m.email,
        bio=m.bio,
        color=m.color,
        commission_percent=m.commission_percent,
        is_active=m.is_active,
        calendar_iframe=m.calendar_iframe or "",
        google_calendar_id=m.google_calendar_id or "",
    )

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "components/master_row.html", {"masters": [result]})

    return result


@router.get("/{master_id}", response_model=MasterResponse)
async def get_master(master_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Master, master_id)
    if not m:
        raise HTTPException(404, "Master not found")
    return MasterResponse(
        id=m.id,
        name=m.name,
        phone=m.phone,
        email=m.email,
        bio=m.bio,
        color=m.color,
        commission_percent=m.commission_percent,
        is_active=m.is_active,
        calendar_iframe=m.calendar_iframe or "",
        google_calendar_id=m.google_calendar_id or "",
    )


@router.patch("/{master_id}", response_model=MasterResponse)
async def update_master(master_id: int, data: MasterCreate, db: AsyncSession = Depends(get_db)):
    m = await db.get(Master, master_id)
    if not m:
        raise HTTPException(404, "Master not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(m, key, val)
    await db.commit()
    await db.refresh(m)
    return MasterResponse(
        id=m.id,
        name=m.name,
        phone=m.phone,
        email=m.email,
        bio=m.bio,
        color=m.color,
        commission_percent=m.commission_percent,
        is_active=m.is_active,
        calendar_iframe=m.calendar_iframe or "",
        google_calendar_id=m.google_calendar_id or "",
    )


@router.delete("/{master_id}", status_code=204)
async def delete_master(master_id: int, db: AsyncSession = Depends(get_db)):
    m = await db.get(Master, master_id)
    if not m:
        raise HTTPException(404, "Master not found")
    await db.delete(m)
    await db.commit()


@router.get("/{master_id}/earnings")
async def master_earnings(
    master_id: int,
    date_from: str = "",
    date_to: str = "",
    db: AsyncSession = Depends(get_db),
):
    from app.models.appointment import Appointment
    stmt = select(Appointment).where(
        Appointment.master_id == master_id,
        Appointment.status == "completed",
    )
    if date_from:
        stmt = stmt.where(Appointment.start_time >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(Appointment.start_time <= datetime.fromisoformat(date_to))

    stmt = stmt.order_by(Appointment.start_time.desc())
    result = await db.execute(stmt)
    appointments = result.scalars().all()

    total_earnings = sum(a.master_earnings or 0 for a in appointments)
    total_revenue = sum(a.price or 0 for a in appointments)

    return {
        "master_id": master_id,
        "appointments_count": len(appointments),
        "total_revenue": round(total_revenue, 2),
        "total_earnings": round(total_earnings, 2),
        "appointments": [
            {
                "id": a.id,
                "date": a.start_time.isoformat(),
                "price": a.price,
                "master_earnings": a.master_earnings,
            }
            for a in appointments
        ],
    }
