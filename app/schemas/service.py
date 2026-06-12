from typing import Optional
from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    duration_minutes: int = 60
    price: float = 0.0
    cost_price: float = 0.0
    category: Optional[str] = ""


class ServiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    duration_minutes: int
    price: float
    cost_price: float
    category: Optional[str] = ""
    is_active: bool

    class Config:
        from_attributes = True
