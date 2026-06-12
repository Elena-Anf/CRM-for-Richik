import datetime
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id"), nullable=False)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    price: Mapped[float] = mapped_column(Float, nullable=True, comment="Цена для клиента")
    cost_price: Mapped[float] = mapped_column(Float, nullable=True, default=0.0, comment="Себестоимость")
    master_earnings: Mapped[float] = mapped_column(Float, nullable=True, default=0.0, comment="Заработок мастера")
    google_event_id: Mapped[str] = mapped_column(String(500), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client = relationship("Client", back_populates="appointments")
    pet = relationship("Pet", back_populates="appointments")
    master = relationship("Master", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
