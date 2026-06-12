from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.global_setting import GlobalSetting
from pydantic import BaseModel

router = APIRouter()


class SettingUpdate(BaseModel):
    value: str


@router.get("/{key}")
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    stmt = select(GlobalSetting).where(GlobalSetting.key == key)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    return {"key": key, "value": setting.value if setting else ""}


@router.put("/{key}")
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(GlobalSetting).where(GlobalSetting.key == key)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if not setting:
        setting = GlobalSetting(key=key, value=data.value)
        db.add(setting)
    else:
        setting.value = data.value
    await db.commit()
    return {"key": key, "value": data.value}
