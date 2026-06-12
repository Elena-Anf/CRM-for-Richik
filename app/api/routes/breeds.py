from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.breed import Breed

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


@router.get("/")
async def list_breeds(species: str = "dog", db: AsyncSession = Depends(get_db)):
    stmt = select(Breed).where(Breed.species == species).order_by(Breed.sort_order)
    result = await db.execute(stmt)
    return [
        {"id": b.id, "name": b.name, "species": b.species}
        for b in result.scalars().all()
    ]
