from sqlalchemy import Boolean, Date, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class CalendarDay(Base):
    __tablename__ = "calendar_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped["Date"] = mapped_column(Date, unique=True, index=True, nullable=False)

    is_school_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # exemplo: "FERIADO", "FACULTATIVO", "SABADO_LETIVO", "RECESSO", "AULA_NORMAL"
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="AULA_NORMAL")

    note: Mapped[str | None] = mapped_column(String(255), nullable=True)