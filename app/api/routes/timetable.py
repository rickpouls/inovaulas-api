from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.timetable import TimetableVersion, TimetableEntry

router = APIRouter(prefix="/timetable", tags=["timetable"])


@router.get("/versions", dependencies=[Depends(get_current_user)])
def list_versions(db: Session = Depends(get_db)):
    rows = db.execute(
        select(TimetableVersion).order_by(TimetableVersion.id.desc())
    ).scalars().all()
    return [
        {
            "id": v.id,
            "code": v.code,
            "start_date": str(v.start_date),
            "end_date": str(v.end_date),
            "source": v.source,
            "note": v.note,
        }
        for v in rows
    ]


@router.get("/{timetable_code}", dependencies=[Depends(get_current_user)])
def get_timetable(timetable_code: str, db: Session = Depends(get_db)):
    tv = db.execute(
        select(TimetableVersion).where(TimetableVersion.code == timetable_code)
    ).scalar_one_or_none()

    if not tv:
        raise HTTPException(status_code=404, detail="timetable not found")

    entries = db.execute(
        select(TimetableEntry).where(TimetableEntry.timetable_version_id == tv.id)
    ).scalars().all()

    return {
        "timetable_code": tv.code,
        "entries": [
            {
                "weekday": e.weekday,
                "slot": e.slot,
                "group_code": e.group_code,
                "subject_name": e.subject_name,
                "teacher_name": e.teacher_name,
                "room_name": e.room_name,
            }
            for e in entries
        ],
    }