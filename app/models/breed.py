from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Breed(Base):
    __tablename__ = "breeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    species: Mapped[str] = mapped_column(String(50), nullable=False, default="dog", comment="dog/cat/other")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
