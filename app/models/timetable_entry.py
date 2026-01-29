# app/models/timetable_entry.py
from sqlalchemy import ForeignKey, Integer, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.timetable_version import TimetableVersion

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    timetable_version_id: Mapped[int] = mapped_column(
        ForeignKey("timetable_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # bruto (como veio do CSV)
    group_code: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # NOVO: turma “limpa” tipo 1.18.1I (extraída do group_code)
    class_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    # NOVO: curso derivado do class_code
    course_name: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)

    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    slot: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    subject_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    subject_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    teacher_username: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    teacher_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    room_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    timetable_version: Mapped[TimetableVersion] = relationship()