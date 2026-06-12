from typing import Optional
from pydantic import BaseModel


class MasterCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = ""
    color: Optional[str] = "#4F46E5"
    commission_percent: float = 40.0
    calendar_iframe: Optional[str] = ""
    google_calendar_id: Optional[str] = ""


class MasterResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = ""
    color: str
    commission_percent: float
    is_active: bool
    calendar_iframe: Optional[str] = ""
    google_calendar_id: Optional[str] = ""

    class Config:
        from_attributes = True
