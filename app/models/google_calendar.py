import datetime
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GoogleCalendarSettings(Base):
    __tablename__ = "google_calendar_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id", ondelete="CASCADE"), unique=True, nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=True)
    token_uri: Mapped[str] = mapped_column(String(500), nullable=True, default="https://oauth2.googleapis.com/token")
    client_id: Mapped[str] = mapped_column(String(500), nullable=True)
    client_secret: Mapped[str] = mapped_column(String(500), nullable=True)
    scopes: Mapped[str] = mapped_column(String(500), nullable=True, default="https://www.googleapis.com/auth/calendar")
    calendar_id: Mapped[str] = mapped_column(String(500), nullable=True, default="primary")
    token_expiry: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_connected: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    master = relationship("Master", back_populates="google_settings")
