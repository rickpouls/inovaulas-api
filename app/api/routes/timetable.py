from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.timetable import TimetableVersion, TimetableEntry

router = APIRouter(prefix="/timetable", tags=["timetable"])


# ----------------------------
# Helpers
# ----------------------------
def slugify(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "unknown"


# ----------------------------
# IMPORT (NECESSÁRIO pro sync job)
# ----------------------------
@router.post("/import", status_code=200, dependencies=[Depends(get_current_user)])
def import_timetable(
    payload: List[Dict[str, Any]],
    db: Session = Depends(get_db),
):
    """
    Espera uma lista de linhas (entries) com pelo menos:
      timetable_code, weekday, slot, group_code
    E opcionalmente:
      subject_name, teacher_name, room
    """

    if not payload:
        raise HTTPException(status_code=400, detail="empty payload")

    code = payload[0].get("timetable_code")
    if not code:
        raise HTTPException(status_code=400, detail="timetable_code missing")

    # Upsert TimetableVersion
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

    # Limpa entries anteriores daquela versão
    db.execute(
        delete(TimetableEntry).where(TimetableEntry.timetable_version_id == tv.id)
    )
    db.commit()

    # Insere novos
    entries: List[TimetableEntry] = []
    for row in payload:
        weekday = row.get("weekday")
        slot = row.get("slot")
        group_code = row.get("group_code")

        # campos opcionais que seu script manda
        subject_name = row.get("subject_name")
        teacher_name = row.get("teacher_name")
        room = row.get("room")  # o script manda "room", o model tem room_name/room_code

        if weekday is None or slot is None or not group_code:
            continue

        # se seu model tiver subject_code/teacher_username/room_code etc, ok preencher
        subject_code = row.get("subject_code") or slugify(subject_name or "")
        teacher_username = row.get("teacher_username") or slugify(teacher_name or "")
        room_code = slugify(room) if room else None

        entries.append(
            TimetableEntry(
                timetable_version_id=tv.id,
                weekday=int(weekday),
                slot=str(slot),
                group_code=str(group_code),
                subject_code=str(subject_code) if subject_code else None,
                subject_name=str(subject_name) if subject_name else None,
                teacher_username=str(teacher_username) if teacher_username else None,
                teacher_name=str(teacher_name) if teacher_name else None,
                room_code=room_code,
                room_name=str(room) if room else None,
            )
        )

    db.add_all(entries)
    db.commit()

    return {"ok": True, "timetable_code": tv.code, "entries_inserted": len(entries)}


# ----------------------------
# LIST VERSIONS
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
# GET TIMETABLE (com filtros combináveis)
# ----------------------------
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


# ----------------------------
# GET FILTERS (listas únicas)
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