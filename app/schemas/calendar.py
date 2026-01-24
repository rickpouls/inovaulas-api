from datetime import date
from pydantic import BaseModel

class CalendarDayIn(BaseModel):
    day: date
    is_school_day: bool
    kind: str = "AULA_NORMAL"
    note: str | None = None


class CalendarDayOut(BaseModel):
    id: int
    day: date
    is_school_day: bool
    kind: str
    note: str | None

    class Config:
        from_attributes = True