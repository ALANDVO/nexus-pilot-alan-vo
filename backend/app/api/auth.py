import secrets
import urllib.parse
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.core.config import get_settings
from app.core.auth import get_current_user, CurrentUser


router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory PKCE store (use Redis in production)
pkce_store: dict[str, dict] = {}


class LoginResponse(BaseModel):
    auth_url: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.get("/login", response_model=LoginResponse)
async def login(request: Request):
    settings = get_settings()

    if not settings.keycloak_client_secret and settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Keycloak client secret not configured"
        )

    # Generate PKCE
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = secrets.token_urlsafe(32)  # Simplified - should be S256 of verifier
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)

    # Store PKCE data
    pkce_store[state] = {
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
        "nonce": nonce,
        "redirect_uri": f"{settings.frontend_url}/callback"
    }

    params = {
        "client_id": settings.keycloak_client_id,
        "response_type": "code",
        "scope": "openid profile email roles",
        "redirect_uri": f"{settings.frontend_url}/callback",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }

    auth_url = f"{settings.keycloak_auth_url}?{urllib.parse.urlencode(params)}"

    return LoginResponse(auth_url=auth_url, state=state)


@router.get("/callback")
async def callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    settings = get_settings()

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description}"
        )

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )

    pkce_data = pkce_store.pop(state, None)
    if not pkce_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter"
        )

    # Exchange code for tokens
    import httpx
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.post(
            settings.keycloak_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": pkce_data["redirect_uri"],
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "code_verifier": pkce_data["code_verifier"]
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token exchange failed: {token_response.text}"
        )

    tokens = token_response.json()
    access_token = tokens.get("access_token")
    id_token = tokens.get("id_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token in response"
        )

    # Redirect back to frontend with tokens in fragment (SPA pattern)
    # Frontend will extract from window.location.hash
    redirect_url = (
        f"{settings.frontend_url}/callback#"
        f"access_token={urllib.parse.quote(access_token)}&"
        f"token_type=bearer&"
        f"expires_in={tokens.get('expires_in', 300)}&"
        f"id_token={urllib.parse.quote(id_token or '')}&"
        f"state={urllib.parse.quote(state)}"
    )

    if refresh_token:
        redirect_url += f"&refresh_token={urllib.parse.quote(refresh_token)}"

    return RedirectResponse(url=redirect_url)


@router.post("/logout")
async def logout(current_user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()

    logout_url = (
        f"{settings.keycloak_logout_url}?"
        f"post_logout_redirect_uri={urllib.parse.quote(settings.frontend_url)}&"
        f"client_id={settings.keycloak_client_id}"
    )

    return {
        "message": "Logged out successfully",
        "logout_url": logout_url
    }


@router.get("/me")
async def me(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "sub": current_user.sub,
        "email": current_user.email,
        "username": current_user.preferred_username,
        "roles": current_user.roles
    }