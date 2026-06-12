from typing import Optional
from pydantic import BaseModel, EmailStr


class ClientCreate(BaseModel):
    name: str
    phone: str
    email: Optional[EmailStr] = None
    telegram: Optional[str] = None
    notes: Optional[str] = ""


class ClientResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    telegram: Optional[str] = None
    notes: Optional[str] = ""

    class Config:
        from_attributes = True


class PetCreate(BaseModel):
    client_id: int
    name: str
    species: str = "dog"
    breed: Optional[str] = ""
    weight: Optional[float] = None
    allergies: Optional[str] = ""


class PetResponse(BaseModel):
    id: int
    client_id: int
    name: str
    species: str
    breed: Optional[str] = ""
    weight: Optional[float] = None
    allergies: Optional[str] = ""

    class Config:
        from_attributes = True
