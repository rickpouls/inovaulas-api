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

    # ex: "INFO1", "MA1", etc
    group_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 0=Seg ... 6=Dom (vamos padronizar)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)

    # 1..N (slot do horário)
    slot: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)

    subject_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    teacher_username: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    teacher_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    room_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    timetable_version: Mapped[TimetableVersion] = relationship()