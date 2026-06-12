import datetime
from sqlalchemy import String, Text, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Master(Base):
    __tablename__ = "masters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    bio: Mapped[str] = mapped_column(Text, nullable=True, default="")
    color: Mapped[str] = mapped_column(String(7), nullable=True, default="#4F46E5")
    commission_percent: Mapped[float] = mapped_column(Float, nullable=False, default=40.0, comment="% мастера от услуги")
    google_calendar_id: Mapped[str] = mapped_column(String(500), nullable=True, default="", comment="ID календаря Google")
    calendar_iframe: Mapped[str] = mapped_column(Text, nullable=True, default="", comment="iframe календаря для расписания")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointments = relationship("Appointment", back_populates="master")
    google_settings = relationship("GoogleCalendarSettings", back_populates="master", uselist=False)
