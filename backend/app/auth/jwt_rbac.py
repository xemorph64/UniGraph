from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from ..config import settings


class User(BaseModel):
    user_id: str
    username: str
    role: str


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: datetime


security = HTTPBearer(auto_error=False)


ROLE_PERMISSIONS = {
    "INVESTIGATOR": [
        "read:alerts",
        "read:cases",
        "write:cases",
        "read:graph",
        "read:graph-analytics",
        "read:transactions",
    ],
    "SUPERVISOR": [
        "read:alerts",
        "read:cases",
        "write:cases",
        "read:graph",
        "read:graph-analytics",
        "run:graph-analytics",
        "read:transactions",
        "approve:str",
        "read:reports",
        "write:enforcement",
        "approve:enforcement",
    ],
    "COMPLIANCE_OFFICER": [
        "read:alerts",
        "read:cases",
        "write:cases",
        "read:graph",
        "read:graph-analytics",
        "run:graph-analytics",
        "read:transactions",
        "approve:str",
        "read:reports",
        "write:reports",
        "submit:str",
        "write:enforcement",
        "approve:enforcement",
    ],
    "ADMIN": ["*"],
}


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {"sub": user.user_id, "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    if settings.DEMO_MODE and not credentials:
        return User(user_id="demo_user", username="demo_user", role="ADMIN")
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    payload = decode_token(credentials.credentials)
    return User(user_id=payload.sub, username=payload.sub, role=payload.role)


def require_permission(permission: str):
    def checker(user: User = Depends(get_current_user)):
        user_perms = ROLE_PERMISSIONS.get(user.role, [])
        if "*" not in user_perms and permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return checker
