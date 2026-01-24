import os
import boto3

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

resp = s3.list_objects_v2(Bucket=bucket)

print("OK. Bucket:", bucket)
print("Keys:", [obj["Key"] for obj in resp.get("Contents", [])])
