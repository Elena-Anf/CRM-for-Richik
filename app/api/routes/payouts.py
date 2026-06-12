import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.payout import MasterPayout
from app.models.master import Master
from app.schemas.payout import PayoutCreate, PayoutResponse, PayoutStatusUpdate

router = APIRouter()


@router.get("/", response_model=List[PayoutResponse])
async def list_payouts(
    master_id: int = 0,
    status: str = "",
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MasterPayout)
        .options(joinedload(MasterPayout.master))
        .order_by(MasterPayout.created_at.desc())
    )
    if master_id:
        stmt = stmt.where(MasterPayout.master_id == master_id)
    if status:
        stmt = stmt.where(MasterPayout.status == status)

    result = await db.execute(stmt)
    payouts = result.unique().scalars().all()

    return [
        PayoutResponse(
            id=p.id,
            master_id=p.master_id,
            master_name=p.master.name,
            amount=p.amount,
            period_start=p.period_start,
            period_end=p.period_end,
            status=p.status,
            paid_at=p.paid_at,
            notes=p.notes,
            created_at=p.created_at,
        )
        for p in payouts
    ]


@router.post("/", response_model=PayoutResponse, status_code=201)
async def create_payout(data: PayoutCreate, db: AsyncSession = Depends(get_db)):
    master = await db.get(Master, data.master_id)
    if not master:
        raise HTTPException(404, "Master not found")

    payout = MasterPayout(**data.model_dump())
    db.add(payout)
    await db.commit()
    await db.refresh(payout)

    return PayoutResponse(
        id=payout.id,
        master_id=payout.master_id,
        master_name=master.name,
        amount=payout.amount,
        period_start=payout.period_start,
        period_end=payout.period_end,
        status=payout.status,
        paid_at=payout.paid_at,
        notes=payout.notes,
        created_at=payout.created_at,
    )


@router.patch("/{payout_id}/status", response_model=PayoutResponse)
async def update_payout_status(
    payout_id: int,
    data: PayoutStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MasterPayout)
        .options(joinedload(MasterPayout.master))
        .where(MasterPayout.id == payout_id)
    )
    result = await db.execute(stmt)
    payout = result.unique().scalar_one_or_none()
    if not payout:
        raise HTTPException(404, "Payout not found")

    payout.status = data.status
    if data.status == "paid":
        payout.paid_at = datetime.datetime.now(datetime.timezone.utc)

    await db.commit()
    await db.refresh(payout)

    return PayoutResponse(
        id=payout.id,
        master_id=payout.master_id,
        master_name=payout.master.name,
        amount=payout.amount,
        period_start=payout.period_start,
        period_end=payout.period_end,
        status=payout.status,
        paid_at=payout.paid_at,
        notes=payout.notes,
        created_at=payout.created_at,
    )
