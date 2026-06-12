import datetime
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MasterPayout(Base):
    __tablename__ = "master_payouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("masters.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, comment="Сумма выплаты")
    period_start: Mapped[datetime.date] = mapped_column(nullable=False, comment="Начало периода")
    period_end: Mapped[datetime.date] = mapped_column(nullable=False, comment="Конец периода")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", comment="pending/paid")
    paid_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    master = relationship("Master", backref="payouts")
