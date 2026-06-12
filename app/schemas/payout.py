from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class PayoutCreate(BaseModel):
    master_id: int
    amount: float
    period_start: date
    period_end: date
    notes: Optional[str] = ""


class PayoutResponse(BaseModel):
    id: int
    master_id: int
    master_name: str = ""
    amount: float
    period_start: date
    period_end: date
    status: str
    paid_at: Optional[datetime] = None
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PayoutStatusUpdate(BaseModel):
    status: str = "paid"
