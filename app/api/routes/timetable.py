from __future__ import annotations

import re
from typing import Any, List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.timetable import TimetableVersion, TimetableEntry  # ajuste se o nome do model estiver diferente
from datetime import date

router = APIRouter(prefix="/timetable", tags=["timetable"])


def slugify(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "unknown"


@router.post("/import", status_code=200)
def import_timetable(
    payload: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    payload esperado:
    [
      {
        "timetable_code": "tecnico_2025_v10",
        "weekday": 0..6,
        "slot": "07:30-08:20",
        "group_code": "...",
        "subject_code": "...",
        "teacher_username": "...",
        "room": "..."
      },
      ...
    ]
    """

    if not payload:
        raise HTTPException(status_code=400, detail="empty payload")

    code = payload[0].get("timetable_code")
    if not code:
        raise HTTPException(status_code=400, detail="timetable_code missing")

    # upsert timetable_version por code
    tv = db.execute(select(TimetableVersion).where(TimetableVersion.code == code)).scalar_one_or_none()
    if not tv:
        tv = TimetableVersion(
            code=code,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            source="r2",
            note="import timetable"
        )
        db.add(tv)
        db.commit()
        db.refresh(tv)

    # limpa entries antigos daquela versão
    db.execute(delete(TimetableEntry).where(TimetableEntry.timetable_version_id == tv.id))
    db.commit()

    # insere novos
    entries = []
    for row in payload:
        weekday = row.get("weekday")
        slot = row.get("slot")
        group_code = row.get("group_code")
        subject_code = row.get("subject_code") or slugify(row.get("subject_name") or "")
        teacher_username = row.get("teacher_username") or slugify(row.get("teacher_name") or "")
        room = row.get("room")

        if weekday is None or slot is None or group_code is None:
            continue

        entries.append(TimetableEntry(
            timetable_version_id=tv.id,
            weekday=int(weekday),
            slot=str(slot),  # agora é string OK
            group_code=str(group_code),
            subject_code=str(subject_code),
            subject_name=row.get("subject_name"),
            teacher_username=str(teacher_username) if teacher_username else None,
            teacher_name=row.get("teacher_name"),
            room_code=slugify(room) if room else None,
            room_name=str(room) if room else None,
        ))

    db.add_all(entries)
    db.commit()

    return {"ok": True, "timetable_code": code, "entries_inserted": len(entries)}