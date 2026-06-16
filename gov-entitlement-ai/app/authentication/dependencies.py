# app/authentication/dependencies.py

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.authentication.jwt_handler import verify_token

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):

    token = credentials.credentials

    try:
        payload = verify_token(token)

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username")
        }

    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")