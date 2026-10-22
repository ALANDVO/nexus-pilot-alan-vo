from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import token_validator, get_current_user_payload
from app.models.user import User
from app.models.part import Part
from app.db.session import get_db


settings = get_settings()
security = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, payload: Dict[str, Any], user: Optional[User] = None):
        self.payload = payload
        self.user = user
        self.sub = payload.get("sub")
        self.email = payload.get("email")
        self.preferred_username = payload.get("preferred_username")
        self.roles = token_validator.extract_roles(payload)

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def require_role(self, role: str) -> None:
        if not self.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {role}"
            )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> CurrentUser:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = await get_current_user_payload(credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get or create local user record
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.keycloak_sub == payload["sub"]))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            keycloak_sub=payload["sub"],
            email=payload.get("email", ""),
            username=payload.get("preferred_username", payload.get("sub", "")),
            roles=token_validator.extract_roles(payload)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return CurrentUser(payload, user)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[CurrentUser]:
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(role: str):
    async def role_checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        current_user.require_role(role)
        return current_user
    return role_checker


# Convenience dependencies
require_viewer = require_role("viewer")
require_operator = require_role("operator")
require_admin = require_role("admin")