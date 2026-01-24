#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sync_calendar_from_r2.py

Baixa um XLSX do Cloudflare R2 (S3) e importa a aba "export" para a API InovAulas.

Requisitos (no .venv):
  pip install boto3 openpyxl requests python-dotenv

ENV obrigatórias (R2):
  R2_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
  R2_BUCKET=adm-media-inovaulas
  R2_ACCESS_KEY_ID=...
  R2_SECRET_ACCESS_KEY=...

ENV obrigatórias (API):
  API_BASE_URL=http://127.0.0.1:8000  (ou sua URL do Railway)

ENV opcionais:
  R2_KEY=calendarios/tecnico/current/calendario_academico_tecnico_2026_v3.xlsx
  OUT_PATH=tmp/calendar_current.xlsx
  SHEET_NAME=export
  LOGIN_USERNAME=paulo
  ACCESS_TOKEN=...               (se definido, evita login automático)
  LIMIT_DAYS=2                   (teste: manda só 2 dias)
  BATCH_SIZE=50                  (recomendado 30~100)
  REQUEST_TIMEOUT=120            (segundos)
"""

from __future__ import annotations

import os
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import boto3
import requests
import openpyxl

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


def parse_letivo(value: Any) -> bool:
    """Aceita: sim/nao, true/false, 1/0, etc."""
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in {"sim", "true", "1", "letivo", "yes", "y"}


def parse_date_cell(value: Any) -> Optional[date]:
    """
    Lê datas do Excel/Google exportado. Pode vir como:
    - datetime/date
    - string "01/01/2026" ou "2026-01-01" ou "2026/01/01"
    """
    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    s = str(value).strip()
    if not s:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    return None


def r2_client() -> Any:
    endpoint = env_required("R2_ENDPOINT")
    access_key = env_required("R2_ACCESS_KEY_ID")
    secret_key = env_required("R2_SECRET_ACCESS_KEY")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )


def download_from_r2(bucket: str, key: str, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    s3 = r2_client()
    s3.download_file(bucket, key, out_path)
    print(f"OK download: {key} -> {out_path}")


def read_export_sheet(xlsx_path: str, sheet_name: str = "export") -> List[Dict[str, Any]]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheets = wb.sheetnames
    if sheet_name not in sheets:
        die(f"Aba '{sheet_name}' não encontrada. Abas: {sheets}")

    ws = wb[sheet_name]
    print(f"Aba selecionada: '{sheet_name}'. Abas: {sheets}")

    # Esperado: cabeçalho na linha 1: data | letivo
    headers: Dict[str, int] = {}
    for col in range(1, ws.max_column + 1):
        v = ws.cell(row=1, column=col).value
        if v is None:
            continue
        key = str(v).strip().lower()
        headers[key] = col

    if "data" not in headers or "letivo" not in headers:
        die(
            f"Cabeçalho inválido na aba '{sheet_name}'. "
            f"Precisa ter colunas: data e letivo. Headers encontrados: {list(headers.keys())}"
        )

    col_data = headers["data"]
    col_letivo = headers["letivo"]

    items: List[Dict[str, Any]] = []
    for row in range(2, ws.max_row + 1):
        d = parse_date_cell(ws.cell(row=row, column=col_data).value)
        if d is None:
            continue
        letivo_val = ws.cell(row=row, column=col_letivo).value
        items.append({
            "day": d.isoformat(),
            "is_school_day": bool(parse_letivo(letivo_val)),
        })

    print(f"Linhas lidas: {len(items)}")
    print("Amostra (primeiras 5):")
    print(json.dumps(items[:5], ensure_ascii=False, indent=2))
    return items


def api_login_and_get_token(api_base_url: str, username: str, timeout: int) -> str:
    """
    Faz login no /auth/login (no teu sistema atual pede só username)
    e retorna access_token.
    """
    url = api_base_url.rstrip("/") + "/auth/login"
    resp = requests.post(url, json={"username": username}, timeout=timeout)

    if resp.status_code != 200:
        die(f"Falha no login em {url}. Status {resp.status_code}. Body: {resp.text}")

    data = resp.json()
    token = data.get("access_token")
    if not token:
        die(f"Login retornou sucesso mas sem access_token. Body: {resp.text}")

    return token


def post_calendar_import(
    api_base_url: str,
    token: str,
    payload: List[Dict[str, Any]],
    timeout: int,
) -> Tuple[int, Any]:
    url = api_base_url.rstrip("/") + "/calendar/import"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    return resp.status_code, body


def chunks(lst: List[Dict[str, Any]], size: int) -> List[List[Dict[str, Any]]]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    # Carrega .env automaticamente (se python-dotenv existir)
    if load_dotenv is not None:
        load_dotenv()

    # Config
    request_timeout = int(os.getenv("REQUEST_TIMEOUT", "120"))
    batch_size = int(os.getenv("BATCH_SIZE", "50"))

    # R2
    bucket = env_required("R2_BUCKET")
    r2_key = os.getenv("R2_KEY") or "calendarios/tecnico/current/calendario_academico_tecnico_2026_v3.xlsx"
    out_path = os.getenv("OUT_PATH") or "tmp/calendar_current.xlsx"

    # API
    api_base_url = env_required("API_BASE_URL")  # ex: http://127.0.0.1:8000
    sheet_name = os.getenv("SHEET_NAME") or "export"
    login_username = os.getenv("LOGIN_USERNAME") or "paulo"

    # 1) Baixa
    download_from_r2(bucket=bucket, key=r2_key, out_path=out_path)

    # 2) Lê planilha
    rows = read_export_sheet(out_path, sheet_name=sheet_name)

    # Teste com poucos dias
    limit = os.getenv("LIMIT_DAYS")
    if limit:
        try:
            n = int(limit)
            rows = rows[:n]
            print(f"LIMIT_DAYS aplicado: enviando somente {n} dias.")
        except ValueError:
            die("LIMIT_DAYS deve ser um inteiro (ex: 2, 10, 365)")

    # 3) Token (preferência: ACCESS_TOKEN; senão login automático)
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        token = api_login_and_get_token(api_base_url, login_username, timeout=request_timeout)
        print("OK login automático. Token recebido.")

    # 4) Import em lotes para evitar timeout
    batches = chunks(rows, batch_size)
    print(f"Enviando {len(rows)} registros em {len(batches)} lote(s) (BATCH_SIZE={batch_size}).")

    for i, batch in enumerate(batches, start=1):
        print(f"-> POST lote {i}/{len(batches)} (itens {len(batch)}) ...")
        status_code, body = post_calendar_import(api_base_url, token, batch, timeout=request_timeout)
        print("API status:", status_code)

        if status_code != 200:
            print(json.dumps(body, ensure_ascii=False, indent=2) if isinstance(body, (dict, list)) else body)
            die("API retornou erro no lote. Veja o output acima.", 2)

    print("✅ Importação concluída com sucesso (todos os lotes).")


if __name__ == "__main__":
    main()