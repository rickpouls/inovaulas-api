import os
import boto3
from pathlib import Path

# Qual arquivo vamos baixar (técnico CURRENT)
KEY = os.getenv("R2_KEY", "calendarios/tecnico/current/calendario_academico_tecnico_2026_v3.xlsx")
OUT = os.getenv("OUT_FILE", "tmp/calendar_current.xlsx")

bucket = os.getenv("R2_BUCKET")
endpoint = os.getenv("R2_ENDPOINT")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

missing = [k for k, v in {
    "R2_BUCKET": bucket,
    "R2_ENDPOINT": endpoint,
    "R2_ACCESS_KEY_ID": access_key,
    "R2_SECRET_ACCESS_KEY": secret_key,
}.items() if not v]
if missing:
    raise SystemExit(f"Variáveis ausentes: {', '.join(missing)}")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="auto",
)

Path(OUT).parent.mkdir(parents=True, exist_ok=True)

s3.download_file(bucket, KEY, OUT)

print("OK download")
print("KEY:", KEY)
print("OUT:", OUT)
