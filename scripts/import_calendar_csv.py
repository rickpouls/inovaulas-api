import csv
import requests
from datetime import datetime

API_URL = "http://127.0.0.1:8000/calendar/import"
import os
TOKEN = os.getenv("IMPORT_TOKEN")

if not TOKEN:
    raise SystemExit("IMPORT_TOKEN não definido. Rode: IMPORT_TOKEN=... python3 scripts/import_calendar_csv.py")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

CSV_PATH = "Calendário Acadêmico 2026.xlsx - Table 1.csv"

def parse_bool(value: str) -> bool:
    return value.strip().lower() in ["sim", "true", "1", "letivo"]

data = []

with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        day = datetime.strptime(row["data"], "%d/%m/%Y").date()

        item = {
            "day": day.isoformat(),
            "is_school_day": parse_bool(row.get("letivo", "sim")),
            "kind": row.get("tipo", "AULA_NORMAL"),
            "note": row.get("observacao") or None,
        }

        data.append(item)

response = requests.post(API_URL, json=data, headers=HEADERS)

print("Status:", response.status_code)
print(response.json())