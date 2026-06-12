from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceResponse

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/")
async def list_services(request: Request, db: AsyncSession = Depends(get_db)):
    stmt = select(Service).order_by(Service.name.asc())
    result = await db.execute(stmt)
    data = result.scalars().all()

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "components/service_row.html", {"services": data})

    return data


@router.post("/", status_code=201)
async def create_service(request: Request, data: ServiceCreate, db: AsyncSession = Depends(get_db)):
    s = Service(**data.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "components/service_row.html", {"services": [s]})

    return s


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(Service, service_id)
    if not s:
        raise HTTPException(404, "Service not found")
    return s


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(service_id: int, data: ServiceCreate, db: AsyncSession = Depends(get_db)):
    s = await db.get(Service, service_id)
    if not s:
        raise HTTPException(404, "Service not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(s, key, val)
    await db.commit()
    await db.refresh(s)
    return s


@router.delete("/{service_id}", status_code=204)
async def delete_service(service_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(Service, service_id)
    if not s:
        raise HTTPException(404, "Service not found")
    await db.delete(s)
    await db.commit()
