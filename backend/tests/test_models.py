import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


class TestModels:
    def test_user_model_creation(self):
        from app.models.user import User
        user = User(
            keycloak_sub="test-123",
            email="test@example.com",
            username="testuser",
            roles=["viewer", "operator"]
        )
        assert user.keycloak_sub == "test-123"
        assert user.email == "test@example.com"
        assert user.roles == ["viewer", "operator"]

    def test_part_model_creation(self):
        from app.models.part import Part, PartStatus
        part = Part(
            owner_id=1,
            filename="test.step",
            original_filename="test.step",
            content_type="application/step",
            file_size=1024,
            file_path="/tmp/test.step",
            status=PartStatus.READY
        )
        assert part.status == PartStatus.READY
        assert part.file_size == 1024

    def test_part_status_enum_values(self):
        from app.models.part import PartStatus
        assert PartStatus.UPLOADED.value == "uploaded"
        assert PartStatus.PROCESSING.value == "processing"
        assert PartStatus.READY.value == "ready"
        assert PartStatus.FAILED.value == "failed"

    def test_unfold_job_model_creation(self):
        from app.models.unfold import UnfoldJob, UnfoldJobStatus
        job = UnfoldJob(
            part_id=1,
            k_factor=0.33,
            kerf=0.1,
            status=UnfoldJobStatus.PENDING
        )
        assert job.k_factor == 0.33
        assert job.status == UnfoldJobStatus.PENDING

    def test_unfold_job_status_enum_values(self):
        from app.models.unfold import UnfoldJobStatus
        assert UnfoldJobStatus.PENDING.value == "pending"
        assert UnfoldJobStatus.RUNNING.value == "running"
        assert UnfoldJobStatus.COMPLETED.value == "completed"
        assert UnfoldJobStatus.FAILED.value == "failed"

    def test_unfold_result_model_creation(self):
        from app.models.unfold import UnfoldResult
        result = UnfoldResult(
            job_id=1,
            profile_path="/tmp/profile.dxf",
            bend_lines_path="/tmp/bendlines.dxf",
            blank_area=5000.0,
            volume_conservation_ratio=1.01,
            bend_count=2
        )
        assert result.blank_area == 5000.0
        assert result.bend_count == 2

    def test_bend_record_model_creation(self):
        from app.models.unfold import BendRecord
        bend = BendRecord(
            result_id=1,
            bend_index=0,
            angle_degrees=90.0,
            direction="up",
            inside_radius=2.0,
            bend_allowance=3.5,
            flange_length_side_a=50.0,
            flange_length_side_b=30.0,
            nearest_cut_distance=10.0,
            bend_line_start={"x": 0, "y": 50},
            bend_line_end={"x": 100, "y": 50}
        )
        assert bend.angle_degrees == 90.0
        assert bend.direction == "up"
        assert bend.inside_radius == 2.0


class TestSecurity:
    @pytest.mark.asyncio
    async def test_token_validator_rejects_invalid_token(self):
        from app.core.security import token_validator
        with pytest.raises(Exception):
            await token_validator.validate_token("invalid.token.string")

    @pytest.mark.asyncio
    async def test_token_validator_extracts_roles(self):
        from app.core.security import token_validator
        payload = {
            "realm_access": {"roles": ["viewer", "operator", "admin"]}
        }
        roles = token_validator.extract_roles(payload)
        assert "viewer" in roles
        assert "operator" in roles
        assert "admin" in roles

    @pytest.mark.asyncio
    async def test_token_validator_has_role(self):
        from app.core.security import token_validator
        payload = {"realm_access": {"roles": ["viewer", "operator"]}}
        assert token_validator.has_role(payload, "viewer") is True
        assert token_validator.has_role(payload, "operator") is True
        assert token_validator.has_role(payload, "admin") is False

    def test_current_user_require_role_raises_on_missing(self):
        from app.core.auth import CurrentUser
        payload = {"realm_access": {"roles": ["viewer"]}}
        user = CurrentUser(payload)
        with pytest.raises(Exception) as exc:
            user.require_role("operator")
        assert exc.value.status_code == 403


class TestConfig:
    def test_settings_loads_defaults(self):
        from app.core.config import Settings
        settings = Settings(
            ENV="development",
            SECRET_KEY="test",
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            KEYCLOAK_URL="http://localhost:8080",
            KEYCLOAK_REALM="test",
            KEYCLOAK_CLIENT_ID="test",
            KEYCLOAK_CLIENT_SECRET="test",
            FRONTEND_URL="http://localhost:5173"
        )
        assert settings.env == "development"
        assert settings.keycloak_issuer == "http://localhost:8080/realms/test"
        assert settings.demo_mode_allowed is True

    def test_settings_production_disables_demo(self):
        from app.core.config import Settings
        settings = Settings(
            ENV="production",
            SECRET_KEY="test",
            DATABASE_URL="sqlite+aiosqlite:///test.db",
            KEYCLOAK_URL="http://localhost:8080",
            KEYCLOAK_REALM="test",
            KEYCLOAK_CLIENT_ID="test",
            KEYCLOAK_CLIENT_SECRET="test",
            FRONTEND_URL="http://localhost:5173"
        )
        assert settings.is_production is True
        assert settings.demo_mode_allowed is False