import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "nexus-pilot-api"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "nexus-pilot-alan-vo"
        assert "CAD superpowers" in data["description"]

    @pytest.mark.asyncio
    async def test_login_requires_client_secret_in_production(self, client: AsyncClient, monkeypatch):
        from app.core.config import get_settings
        settings = get_settings()
        original_env = settings.env
        settings.env = "production"
        try:
            response = await client.get("/auth/login")
            assert response.status_code == 500
        finally:
            settings.env = original_env

    @pytest.mark.asyncio
    async def test_login_returns_auth_url_in_dev(self, client: AsyncClient, monkeypatch):
        from app.core.config import get_settings
        settings = get_settings()
        original_env = settings.env
        settings.env = "development"
        settings.keycloak_client_secret = "test-secret"
        try:
            response = await client.get("/auth/login")
            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "state" in data
            assert "keycloak" in data["auth_url"].lower()
        finally:
            settings.env = original_env

    @pytest.mark.asyncio
    async def test_callback_missing_code_returns_400(self, client: AsyncClient):
        response = await client.get("/auth/callback")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_invalid_state_returns_400(self, client: AsyncClient):
        response = await client.get("/auth/callback?code=test&state=invalid")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_logout_requires_auth(self, client: AsyncClient):
        response = await client.post("/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_requires_auth(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401