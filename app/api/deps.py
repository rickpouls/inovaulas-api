from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import verify
from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    payload = verify(credentials.credentials, settings.AUTH_SECRET)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")

    return payload