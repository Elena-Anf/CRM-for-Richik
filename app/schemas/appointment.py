from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    client_name: str = Field(..., max_length=255)
    client_phone: str = Field(..., max_length=20)
    client_email: Optional[str] = Field(None, max_length=255)
    pet_name: str = Field(..., max_length=255)
    pet_species: str = Field(default="dog", max_length=50)
    pet_breed: Optional[str] = Field(default="", max_length=255)
    master_id: int
    service_id: int
    start_time: datetime
    notes: Optional[str] = ""
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None


class AppointmentResponse(BaseModel):
    id: int
    client_name: str
    client_phone: str
    pet_name: str
    pet_species: str
    pet_breed: Optional[str] = ""
    master_id: int
    master_name: str
    service_id: int
    service_name: str
    start_time: datetime
    end_time: datetime
    status: str
    price: Optional[float] = None
    cost_price: Optional[float] = 0.0
    master_earnings: Optional[float] = 0.0
    notes: Optional[str] = ""
    google_event_id: Optional[str] = None

    class Config:
        from_attributes = True


class AppointmentUpdate(BaseModel):
    client_name: Optional[str] = Field(None, max_length=255)
    client_phone: Optional[str] = Field(None, max_length=20)
    pet_name: Optional[str] = Field(None, max_length=255)
    pet_species: Optional[str] = Field(None, max_length=50)
    pet_breed: Optional[str] = Field(None, max_length=255)
    master_id: Optional[int] = None
    service_id: Optional[int] = None
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = Field(None, pattern="^(pending|confirmed|completed|cancelled)$")
    notes: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None


class AppointmentReschedule(BaseModel):
    start_time: datetime


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|confirmed|completed|cancelled)$")


class AppointmentFinance(BaseModel):
    id: int
    price: float
    cost_price: float
    master_earnings: float
    profit: float
    status: str
