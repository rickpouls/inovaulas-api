from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

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
def get_timetable(
    timetable_code: str,
    group: str | None = Query(None, description="Filtro por turma (group_code)"),
    teacher: str | None = Query(None, description="Filtro por professor (teacher_name)"),
    room: str | None = Query(None, description="Filtro por local (room_name)"),
    weekday: int | None = Query(None, ge=0, le=6, description="0=Seg ... 6=Dom"),
    db: Session = Depends(get_db),
):
    tv = db.execute(
        select(TimetableVersion).where(TimetableVersion.code == timetable_code)
    ).scalar_one_or_none()

    if not tv:
        raise HTTPException(status_code=404, detail="timetable not found")

    q = select(TimetableEntry).where(TimetableEntry.timetable_version_id == tv.id)

    # filtros combináveis
    if group:
        q = q.where(TimetableEntry.group_code.ilike(f"%{group}%"))

    if teacher:
        q = q.where(TimetableEntry.teacher_name.ilike(f"%{teacher}%"))

    if room:
        q = q.where(TimetableEntry.room_name.ilike(f"%{room}%"))

    if weekday is not None:
        q = q.where(TimetableEntry.weekday == weekday)

    q = q.order_by(TimetableEntry.weekday, TimetableEntry.slot, TimetableEntry.group_code)

    entries = db.execute(q).scalars().all()

    return {
        "timetable_code": tv.code,
        "filters": {"group": group, "teacher": teacher, "room": room, "weekday": weekday},
        "count": len(entries),
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


@router.get("/{timetable_code}/filters", dependencies=[Depends(get_current_user)])
def get_filters(timetable_code: str, db: Session = Depends(get_db)):
    tv = db.execute(
        select(TimetableVersion).where(TimetableVersion.code == timetable_code)
    ).scalar_one_or_none()

    if not tv:
        raise HTTPException(status_code=404, detail="timetable not found")

    base = (
        select(
            TimetableEntry.group_code,
            TimetableEntry.teacher_name,
            TimetableEntry.room_name,
        )
        .where(TimetableEntry.timetable_version_id == tv.id)
        .subquery()
    )

    groups = db.execute(
        select(base.c.group_code)
        .where(base.c.group_code.is_not(None))
        .where(func.length(func.trim(base.c.group_code)) > 0)
        .distinct()
        .order_by(base.c.group_code)
    ).scalars().all()

    teachers = db.execute(
        select(base.c.teacher_name)
        .where(base.c.teacher_name.is_not(None))
        .where(func.length(func.trim(base.c.teacher_name)) > 0)
        .distinct()
        .order_by(base.c.teacher_name)
    ).scalars().all()

    rooms = db.execute(
        select(base.c.room_name)
        .where(base.c.room_name.is_not(None))
        .where(func.length(func.trim(base.c.room_name)) > 0)
        .distinct()
        .order_by(base.c.room_name)
    ).scalars().all()

    return {
        "timetable_code": tv.code,
        "groups": groups,
        "teachers": teachers,
        "rooms": rooms,
        "weekdays": [0, 1, 2, 3, 4, 5, 6],
    }