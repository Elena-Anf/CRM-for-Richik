import datetime
from sqlalchemy import String, Text, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False, default="dog")
    breed: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    weight: Mapped[float] = mapped_column(Float, nullable=True)
    color: Mapped[str] = mapped_column(String(255), nullable=True, default="")
    birth_date: Mapped[datetime.date] = mapped_column(nullable=True)
    allergies: Mapped[str] = mapped_column(Text, nullable=True, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    photo_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="pets")
    appointments = relationship("Appointment", back_populates="pet")
