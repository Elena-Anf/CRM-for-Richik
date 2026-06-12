from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.master import Master
from app.models.service import Service
from app.models.client import Client
from app.models.appointment import Appointment
from app.models.pet import Pet

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    masters_count = (await db.execute(select(func.count(Master.id)))).scalar()
    services_count = (await db.execute(select(func.count(Service.id)))).scalar()
    clients_count = (await db.execute(select(func.count(Client.id)))).scalar()
    appointments_today_count = (
        await db.execute(
            select(func.count(Appointment.id))
        )
    ).scalar()

    return templates.TemplateResponse(request, "pages/index.html", {
        "stats": {
            "masters": masters_count,
            "services": services_count,
            "clients": clients_count,
            "appointments_today": appointments_today_count,
        },
    })


@router.get("/booking", response_class=HTMLResponse, include_in_schema=False)
async def booking_page(request: Request, db: AsyncSession = Depends(get_db)):
    masters = (await db.execute(select(Master).where(Master.is_active == True))).scalars().all()
    services = (await db.execute(select(Service).where(Service.is_active == True))).scalars().all()
    return templates.TemplateResponse(request, "pages/booking.html", {
        "masters": masters,
        "services": services,
    })


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_page(
    request: Request,
    status: str = "",
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
    if status:
        stmt = stmt.where(Appointment.status == status)
    stmt = stmt.order_by(Appointment.start_time.desc()).limit(50)
    result = await db.execute(stmt)
    appointments = result.unique().scalars().all()
    return templates.TemplateResponse(request, "pages/admin.html", {
        "appointments": appointments,
    })


@router.get("/schedule", response_class=HTMLResponse, include_in_schema=False)
async def schedule_page(request: Request, db: AsyncSession = Depends(get_db)):
    masters = (await db.execute(
        select(Master).order_by(Master.name)
    )).scalars().all()
    return templates.TemplateResponse(request, "pages/schedule.html", {"masters": masters})


@router.get("/admin/masters", response_class=HTMLResponse, include_in_schema=False)
async def admin_masters(request: Request, db: AsyncSession = Depends(get_db)):
    masters = (await db.execute(
        select(Master).order_by(Master.name)
    )).unique().scalars().all()
    return templates.TemplateResponse(request, "pages/masters.html", {"masters": masters})


@router.get("/admin/services", response_class=HTMLResponse, include_in_schema=False)
async def admin_services(request: Request, db: AsyncSession = Depends(get_db)):
    services = (await db.execute(select(Service).order_by(Service.name))).scalars().all()
    return templates.TemplateResponse(request, "pages/services.html", {"services": services})


@router.get("/admin/clients", response_class=HTMLResponse, include_in_schema=False)
async def admin_clients(request: Request, db: AsyncSession = Depends(get_db)):
    clients = (await db.execute(
        select(Client).order_by(Client.name)
    )).scalars().all()
    return templates.TemplateResponse(request, "pages/clients.html", {"clients": clients})
