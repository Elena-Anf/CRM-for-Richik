import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Цена для клиента")
    cost_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="Себестоимость (материалы)")
    category: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointments = relationship("Appointment", back_populates="service")
