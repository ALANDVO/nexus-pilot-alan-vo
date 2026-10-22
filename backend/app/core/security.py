import time
import httpx
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from jose.utils import base64url_decode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.core.config import get_settings


class JWKSClient:
    def __init__(self, jwks_url: str, cache_ttl: int = 3600):
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0

    async def get_signing_key(self, kid: str) -> Optional[rsa.RSAPublicKey]:
        jwks = await self._fetch_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return self._jwk_to_rsa_public_key(key)
        return None

    async def _fetch_jwks(self) -> Dict[str, Any]:
        now = time.time()
        if self._cache and (now - self._cache_time) < self.cache_ttl:
            return self._cache

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            self._cache = response.json()
            self._cache_time = now
            return self._cache

    def _jwk_to_rsa_public_key(self, jwk: Dict[str, Any]) -> rsa.RSAPublicKey:
        n = base64url_decode(jwk["n"].encode())
        e = base64url_decode(jwk["e"].encode())
        n_int = int.from_bytes(n, "big")
        e_int = int.from_bytes(e, "big")
        public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
        return public_numbers.public_key()


class TokenValidator:
    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.jwks_client = JWKSClient(self.settings.keycloak_jwks_url)

    async def validate_token(self, token: str) -> Dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise JWTError("Token missing kid header")

            signing_key = await self.jwks_client.get_signing_key(kid)
            if not signing_key:
                raise JWTError(f"Signing key not found for kid: {kid}")

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.keycloak_client_id,
                issuer=self.settings.keycloak_issuer,
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True}
            )
            return payload
        except JWTError as e:
            raise JWTError(f"Token validation failed: {e}")

    def extract_roles(self, payload: Dict[str, Any]) -> list[str]:
        realm_access = payload.get("realm_access", {})
        return realm_access.get("roles", [])

    def has_role(self, payload: Dict[str, Any], required_role: str) -> bool:
        roles = self.extract_roles(payload)
        return required_role in roles


token_validator = TokenValidator()


async def get_current_user_payload(token: str) -> Dict[str, Any]:
    return await token_validator.validate_token(token)