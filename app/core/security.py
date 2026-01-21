import os
import time
import hmac
import hashlib
import base64
import json
from typing import Any, Dict, Optional

# ⚠️ Simples e direto (sem libs externas).
# Depois a gente troca por JWT de verdade, se quiser.

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))

def sign(payload: Dict[str, Any], secret: str, ttl_seconds: int = 60 * 60 * 24) -> str:
    now = int(time.time())
    body = {
        "iat": now,
        "exp": now + int(ttl_seconds),
        **payload,
    }
    msg = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    return _b64url_encode(msg) + "." + _b64url_encode(sig)

def verify(token: str, secret: str) -> Optional[Dict[str, Any]]:
    try:
        msg_b64, sig_b64 = token.split(".", 1)
        msg = _b64url_decode(msg_b64)
        sig = _b64url_decode(sig_b64)

        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None

        payload = json.loads(msg.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None