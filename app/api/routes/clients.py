from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.client import Client
from app.models.pet import Pet
from app.schemas.client import ClientCreate, ClientResponse, PetCreate, PetResponse

router = APIRouter()


@router.get("/", response_model=List[ClientResponse])
async def list_clients(search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db)):
    stmt = select(Client)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            Client.name.ilike(like) | Client.phone.ilike(like)
        )
    stmt = stmt.order_by(Client.name.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Client, client_id)
    if not c:
        raise HTTPException(404, "Client not found")
    return c


@router.post("/", response_model=ClientResponse, status_code=201)
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    c = Client(**data.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.get("/{client_id}/pets", response_model=List[PetResponse])
async def list_client_pets(client_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Pet).where(Pet.client_id == client_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{client_id}/pets", response_model=PetResponse, status_code=201)
async def add_pet(client_id: int, data: PetCreate, db: AsyncSession = Depends(get_db)):
    data.client_id = client_id
    p = Pet(**data.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/{client_id}", status_code=204)
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Client, client_id)
    if not c:
        raise HTTPException(404, "Client not found")
    await db.delete(c)
    await db.commit()


@router.delete("/pets/{pet_id}", status_code=204)
async def delete_pet(pet_id: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Pet, pet_id)
    if not p:
        raise HTTPException(404, "Pet not found")
    await db.delete(p)
    await db.commit()
