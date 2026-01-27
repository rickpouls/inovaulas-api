#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import json
import re
from typing import Any, Dict, List, Tuple

import boto3
import requests
import csv

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


# ----------------------------
# Helpers
# ----------------------------

def die(msg: str, code: int = 1) -> None:
    print(f"[ERRO] {msg}")
    raise SystemExit(code)


def env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        die(f"Variável de ambiente obrigatória não definida: {name}")
    return v


def norm(s: Any) -> str:
    return ("" if s is None else str(s)).strip()


# ----------------------------
# R2
# ----------------------------

def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=env_required("R2_ENDPOINT"),
        aws_access_key_id=env_required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=env_required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def download_from_r2(bucket: str, key: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    r2_client().download_file(bucket, key, out_path)
    print(f"OK download: {key}")


def load_index_json(bucket: str, index_key: str) -> Dict[str, Any]:
    tmp_path = "tmp/index_timetable.json"
    download_from_r2(bucket, index_key, tmp_path)
    with open(tmp_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------------
# Parsing (CSV -> API schema)
# ----------------------------

_WEEKDAY_MAP = {
    # 0 = Monday
    "segunda": 0, "segunda-feira": 0, "seg": 0,
    "terca": 1, "terça": 1, "terça-feira": 1, "terca-feira": 1, "ter": 1,
    "quarta": 2, "quarta-feira": 2, "qua": 2,
    "quinta": 3, "quinta-feira": 3, "qui": 3,
    "sexta": 4, "sexta-feira": 4, "sex": 4,
    "sabado": 5, "sábado": 5, "sábado-feira": 5, "sab": 5,
    "domingo": 6, "dom": 6,
}

def parse_weekday(day_raw: str) -> int | None:
    d = norm(day_raw).lower()
    d = d.replace("feira", "feira")  # noop só pra ficar explícito
    d = d.replace("  ", " ").strip()
    # exemplos seus: "Sexta feira", "Quarta-feira"
    d = d.replace(" feira", "-feira")
    d = d.replace("--", "-")
    d = d.replace("á", "a").replace("ã", "a").replace("ç", "c").replace("é", "e").replace("ê", "e").replace("í", "i").replace("ó", "o").replace("ô", "o").replace("ú", "u")
    return _WEEKDAY_MAP.get(d)


def parse_slot(hour_raw: str) -> str | None:
    """
    Aceita coisas tipo:
      - 07h30-8h20min
      - 8h20-9h10min
      - 14h10-15h00min
    Converte para:
      - 07:30-08:20
      - 08:20-09:10
      - 14:10-15:00
    """
    s = norm(hour_raw).lower()
    s = s.replace("min", "").replace(" ", "")
    # pega "07h30-8h20" etc
    m = re.match(r"^(\d{1,2})h(\d{2})-(\d{1,2})h(\d{2})$", s)
    if not m:
        return None
    h1, m1, h2, m2 = m.groups()
    return f"{int(h1):02d}:{int(m1):02d}-{int(h2):02d}:{int(m2):02d}"


def read_timetable_csv_and_transform(csv_path: str, timetable_code: str) -> List[Dict[str, Any]]:
    """
    Lê o CSV "cru" e devolve List[Dict] no formato aceito pela API.
    """
    out: List[Dict[str, Any]] = []

    # utf-8-sig remove BOM (aquele caractere invisível que aparece na primeira coluna)
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = norm(row.get("Day"))
            hour = norm(row.get("Hour"))
            group = norm(row.get("Students Sets"))
            subject = norm(row.get("Subject"))
            teacher = norm(row.get("Teachers"))
            room = norm(row.get("Room"))

            weekday = parse_weekday(day)
            slot = parse_slot(hour)

            if weekday is None or slot is None or not group:
                # pula linha inválida (mas não mata o processo)
                continue

            out.append({
                "timetable_code": timetable_code,
                "weekday": weekday,
                "slot": slot,
                "group_code": group,
                # pode mandar subject_code/teacher_username, mas sua API também aceita *_name
                "subject_name": subject,
                "teacher_name": teacher,
                "room": room or None,
            })

    print(f"Linhas do CSV lidas e convertidas: {len(out)}")
    print("Amostra convertida (primeiras 3):")
    print(json.dumps(out[:3], ensure_ascii=False, indent=2))
    return out


# ----------------------------
# API
# ----------------------------

def api_login_and_get_token(api_base_url: str, username: str) -> str:
    url = api_base_url.rstrip("/") + "/auth/login"
    resp = requests.post(url, json={"username": username}, timeout=30)
    if resp.status_code != 200:
        die(f"Falha no login. Status {resp.status_code}: {resp.text}")

    token = resp.json().get("access_token")
    if not token:
        die("Login OK, mas access_token ausente")
    return token


def post_timetable_import(api_base_url: str, token: str, payload: List[Dict[str, Any]]) -> Tuple[int, Any]:
    url = api_base_url.rstrip("/") + "/timetable/import"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    # NÃO precisa params=... porque a API pega timetable_code do body
    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    if load_dotenv:
        load_dotenv()

    bucket = env_required("R2_BUCKET")
    api_base_url = env_required("API_BASE_URL")

    # técnico | superior (controla qual index.json baixar)
    timetable_type = os.getenv("TIMETABLE_TYPE", "tecnico").strip().lower()

    # este é o código que vai para a API (e vai virar TimetableVersion.code)
    # você pode setar manualmente no .env: TIMETABLE_CODE=tecnico_2026_v2 (ex.)
    timetable_code = os.getenv("TIMETABLE_CODE") or f"{timetable_type}_2026"

    index_key = f"horarios/{timetable_type}/index.json"
    out_csv = f"tmp/timetable_{timetable_type}.csv"

    login_username = os.getenv("LOGIN_USERNAME", "paulo")

    index_data = load_index_json(bucket, index_key)
    csv_key = index_data.get("current_key")
    if not csv_key:
        die("index.json sem current_key")

    download_from_r2(bucket, csv_key, out_csv)

    payload_rows = read_timetable_csv_and_transform(out_csv, timetable_code)

    if not payload_rows:
        die("Nenhuma linha válida após conversão (weekday/slot/group_code). Verifique CSV.")

    token = os.getenv("ACCESS_TOKEN")
    if not token:
        token = api_login_and_get_token(api_base_url, login_username)
        print("OK login automático. Token recebido.")

    status, body = post_timetable_import(api_base_url, token, payload_rows)

    print("API status:", status)
    print(json.dumps(body, ensure_ascii=False, indent=2) if isinstance(body, (dict, list)) else body)

    if status != 200:
        die("Erro na importação de horários", 2)

    print("✅ Importação de horários concluída com sucesso.")


if __name__ == "__main__":
    main()