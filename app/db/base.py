from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

from app.models.calendar_day import CalendarDay
from app.models.timetable_version import TimetableVersion
from app.models.timetable_entry import TimetableEntry
from app.models.class_session import ClassSession