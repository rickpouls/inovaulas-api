# app/api/routes/timetable.py
from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.timetable import TimetableEntry, TimetableVersion

router = APIRouter(prefix="/timetable", tags=["timetable"])


# ----------------------------
# Helpers (turma/código/curso)
# ----------------------------

_CLASS_CODE_RE = re.compile(r"\((\d+\.\d+\.\d+[A-Za-z])\)")

def extract_class_code(group_code: str | None) -> str | None:
    """
    Extrai '1.18.1I' de strings como:
      '1º INFOR_M(1.18.1I) sala-03'
    """
    if not group_code:
        return None
    m = _CLASS_CODE_RE.search(group_code)
    return m.group(1).upper() if m else None


def course_from_class_code(class_code: str | None) -> str | None:
    """
    Regra: x.18.y = Informática | x.28.y = Meio Ambiente
    """
    if not class_code:
        return None
    parts = class_code.split(".")
    if len(parts) < 2:
        return None
    return {"18": "Informática", "28": "Meio Ambiente"}.get(parts[1])


def slugify(text: str | None) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "unknown"


# ----------------------------
# GET: versions
# ----------------------------

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


# ----------------------------
# GET: filters (listas únicas)
# ----------------------------

@router.get("/{timetable_code}/filters", dependencies=[Depends(get_current_user)])
def get_filters(timetable_code: str, db: Session = Depends(get_db)):
    tv = db.execute(
        select(TimetableVersion).where(TimetableVersion.code == timetable_code)
    ).scalar_one_or_none()

    if not tv:
        raise HTTPException(status_code=404, detail="timetable not found")

    base = (
        select(
            TimetableEntry.class_code,
            TimetableEntry.course_name,
            TimetableEntry.teacher_name,
            TimetableEntry.room_name,
        )
        .where(TimetableEntry.timetable_version_id == tv.id)
        .subquery()
    )

    class_codes = db.execute(
        select(base.c.class_code)
        .where(base.c.class_code.is_not(None))
        .where(func.length(func.trim(base.c.class_code)) > 0)
        .distinct()
        .order_by(base.c.class_code)
    ).scalars().all()

    courses = db.execute(
        select(base.c.course_name)
        .where(base.c.course_name.is_not(None))
        .where(func.length(func.trim(base.c.course_name)) > 0)
        .distinct()
        .order_by(base.c.course_name)
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
        "class_codes": class_codes,   # turma limpa: 1.18.1I etc
        "courses": courses,           # Informática / Meio Ambiente
        "teachers": teachers,
        "rooms": rooms,
        "weekdays": [0, 1, 2, 3, 4, 5, 6],
    }


# ----------------------------
# GET: timetable (com filtros combináveis)
# ----------------------------

@router.get("/{timetable_code}", dependencies=[Depends(get_current_user)])
def get_timetable(
    timetable_code: str,
    group: str | None = Query(None, description="Turma (class_code). Ex: 1.18.1I"),
    course: str | None = Query(None, description="Curso. Ex: Informática | Meio Ambiente"),
    teacher: str | None = Query(None, description="Professor (contém)"),
    room: str | None = Query(None, description="Local (contém)"),
    weekday: int | None = Query(None, ge=0, le=6, description="0=Seg ... 6=Dom"),
    db: Session = Depends(get_db),
):
    tv = db.execute(
        select(TimetableVersion).where(TimetableVersion.code == timetable_code)
    ).scalar_one_or_none()

    if not tv:
        raise HTTPException(status_code=404, detail="timetable not found")

    q = select(TimetableEntry).where(TimetableEntry.timetable_version_id == tv.id)

    if group:
        q = q.where(TimetableEntry.class_code == group.upper())

    if course:
        q = q.where(TimetableEntry.course_name == course)

    if teacher:
        q = q.where(TimetableEntry.teacher_name.ilike(f"%{teacher}%"))

    if room:
        q = q.where(TimetableEntry.room_name.ilike(f"%{room}%"))

    if weekday is not None:
        q = q.where(TimetableEntry.weekday == weekday)

    q = q.order_by(
        TimetableEntry.weekday,
        TimetableEntry.slot,
        TimetableEntry.class_code,
    )

    entries = db.execute(q).scalars().all()

    return {
        "timetable_code": tv.code,
        "filters": {
            "group": group.upper() if group else None,
            "course": course,
            "teacher": teacher,
            "room": room,
            "weekday": weekday,
        },
        "count": len(entries),
        "entries": [
            {
                "weekday": e.weekday,
                "slot": e.slot,
                "class_code": e.class_code,
                "course_name": e.course_name,
                "subject_name": e.subject_name,
                "teacher_name": e.teacher_name,
                "room_name": e.room_name,
                "group_code_raw": e.group_code,
            }
            for e in entries
        ],
    }


# ----------------------------
# POST: import (script manda payload)
# ----------------------------

@router.post("/import", status_code=200, dependencies=[Depends(get_current_user)])
def import_timetable(
    payload: List[Dict[str, Any]],
    db: Session = Depends(get_db),
):
    if not payload:
        raise HTTPException(status_code=400, detail="empty payload")

    code = payload[0].get("timetable_code")
    if not code:
        raise HTTPException(status_code=400, detail="timetable_code missing")

    tv = db.execute(
        select(TimetableVersion).where(TimetableVersion.code == code)
    ).scalar_one_or_none()

    if not tv:
        tv = TimetableVersion(
            code=code,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            source="r2",
            note="import timetable",
        )
        db.add(tv)
        db.commit()
        db.refresh(tv)

    db.execute(delete(TimetableEntry).where(TimetableEntry.timetable_version_id == tv.id))
    db.commit()

    entries: List[TimetableEntry] = []

    for row in payload:
        weekday = row.get("weekday")
        slot = row.get("slot")
        group_code = row.get("group_code")

        subject_name = row.get("subject_name")
        teacher_name = row.get("teacher_name")
        room = row.get("room")

        if weekday is None or slot is None or group_code is None:
            continue

        class_code = extract_class_code(group_code)
        course_name = course_from_class_code(class_code)

        entries.append(
            TimetableEntry(
                timetable_version_id=tv.id,
                weekday=int(weekday),
                slot=str(slot),

                group_code=str(group_code),
                class_code=class_code,
                course_name=course_name,

                subject_code=slugify(subject_name),
                subject_name=subject_name,

                teacher_username=slugify(teacher_name) if teacher_name else None,
                teacher_name=teacher_name,

                room_code=slugify(room) if room else None,
                room_name=str(room) if room else None,
            )
        )

    db.add_all(entries)
    db.commit()

    return {"ok": True, "timetable_code": code, "entries_inserted": len(entries)}