from sqlalchemy import Date, ForeignKey, Integer, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    day: Mapped["Date"] = mapped_column(Date, nullable=False, index=True)

    group_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    slot: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)

    subject_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    teacher_username: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    teacher_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    room_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # "prevista", "realizada", "cancelada", "substituida", "reposta", "antecipada"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="prevista", index=True)

    # ligações (reposicao/antecipacao apontam para a aula “origem”)
    origin_session_id: Mapped[int | None] = mapped_column(ForeignKey("class_sessions.id"), nullable=True)