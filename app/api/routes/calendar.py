from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.calendar_day import CalendarDay
from app.schemas.calendar import CalendarDayIn, CalendarDayOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/import", response_model=list[CalendarDayOut])
def import_calendar(
    payload: list[CalendarDayIn],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    created = []

    for item in payload:
        exists = db.execute(
            select(CalendarDay).where(CalendarDay.day == item.day)
        ).scalar_one_or_none()

        if exists:
            exists.is_school_day = item.is_school_day
            exists.kind = item.kind
            exists.note = item.note
            created.append(exists)
        else:
            day = CalendarDay(
                day=item.day,
                is_school_day=item.is_school_day,
                kind=item.kind,
                note=item.note,
            )
            db.add(day)
            created.append(day)

    db.commit()
    return created


@router.get("", response_model=list[CalendarDayOut])
def list_calendar(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.execute(
        select(CalendarDay).order_by(CalendarDay.day)
    ).scalars().all()