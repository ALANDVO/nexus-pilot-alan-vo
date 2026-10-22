import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.part import Part, PartStatus
from app.models.user import User
from app.models.unfold import UnfoldJob, UnfoldResult, BendRecord, UnfoldJobStatus


class TestPartsAPI:
    @pytest.mark.asyncio
    async def test_upload_part_requires_operator_role(self, client: AsyncClient, mock_token_validator):
        from app.core.auth import token_validator
        async def mock_validate(token):
            return {
                "sub": "viewer-only",
                "email": "viewer@example.com",
                "preferred_username": "viewer",
                "realm_access": {"roles": ["viewer"]},
                "aud": "test-client",
                "iss": "http://localhost:8080/realms/test"
            }
        token_validator.validate_token = mock_validate

        files = {"file": ("test.step", b"STEP content", "application/step")}
        response = await client.post("/api/parts", files=files)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_part_rejects_invalid_extension(self, client: AsyncClient, mock_token_validator):
        files = {"file": ("test.txt", b"text content", "text/plain")}
        response = await client.post("/api/parts", files=files)
        assert response.status_code == 400
        assert "STEP files" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_parts_requires_viewer_role(self, client: AsyncClient, mock_token_validator):
        from app.core.auth import token_validator
        async def mock_validate(token):
            return {
                "sub": "no-role",
                "email": "norole@example.com",
                "preferred_username": "norole",
                "realm_access": {"roles": []},
                "aud": "test-client",
                "iss": "http://localhost:8080/realms/test"
            }
        token_validator.validate_token = mock_validate

        response = await client.get("/api/parts")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_parts_returns_paginated_results(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User
    ):
        # Create multiple parts
        for i in range(5):
            part = Part(
                owner_id=test_user.id,
                filename=f"part_{i}.step",
                original_filename=f"part_{i}.step",
                content_type="application/step",
                file_size=1024,
                file_path=f"/tmp/part_{i}.step",
                status=PartStatus.READY
            )
            db_session.add(part)
        await db_session.commit()

        response = await client.get("/api/parts?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["parts"]) == 3
        assert data["limit"] == 3

    @pytest.mark.asyncio
    async def test_get_part_returns_404_for_other_user(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User
    ):
        from app.models.user import User as UserModel
        other_user = UserModel(
            keycloak_sub="other-sub",
            email="other@example.com",
            username="other",
            roles=["operator"]
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        part = Part(
            owner_id=other_user.id,
            filename="other.step",
            original_filename="other.step",
            content_type="application/step",
            file_size=1024,
            file_path="/tmp/other.step",
            status=PartStatus.READY
        )
        db_session.add(part)
        await db_session.commit()
        await db_session.refresh(part)

        response = await client.get(f"/api/parts/{part.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_part_removes_record(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User, test_part: Part
    ):
        response = await client.delete(f"/api/parts/{test_part.id}")
        assert response.status_code == 204

        result = await db_session.execute(select(Part).where(Part.id == test_part.id))
        assert result.scalar_one_or_none() is None


class TestUnfoldAPI:
    @pytest.mark.asyncio
    async def test_start_unfold_requires_ready_part(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User
    ):
        part = Part(
            owner_id=test_user.id,
            filename="not_ready.step",
            original_filename="not_ready.step",
            content_type="application/step",
            file_size=1024,
            file_path="/tmp/not_ready.step",
            status=PartStatus.UPLOADED
        )
        db_session.add(part)
        await db_session.commit()
        await db_session.refresh(part)

        response = await client.post(
            f"/api/parts/{part.id}/unfold",
            json={"k_factor": 0.33, "kerf": 0.1}
        )
        assert response.status_code == 400
        assert "not ready" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_start_unfold_validates_k_factor_range(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User, test_part: Part
    ):
        response = await client.post(
            f"/api/parts/{test_part.id}/unfold",
            json={"k_factor": 1.5, "kerf": 0.1}
        )
        assert response.status_code == 422

        response = await client.post(
            f"/api/parts/{test_part.id}/unfold",
            json={"k_factor": -0.1, "kerf": 0.1}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_unfold_result_returns_job_status(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User, test_part: Part
    ):
        job = UnfoldJob(
            part_id=test_part.id,
            k_factor=0.33,
            kerf=0.0,
            status=UnfoldJobStatus.COMPLETED
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.get(f"/api/parts/{test_part.id}/unfold/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_unfold_result_returns_bends_when_completed(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User, test_part: Part
    ):
        job = UnfoldJob(
            part_id=test_part.id,
            k_factor=0.33,
            kerf=0.0,
            status=UnfoldJobStatus.COMPLETED
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        result = UnfoldResult(
            job_id=job.id,
            profile_path="/tmp/profile.dxf",
            bend_lines_path="/tmp/bendlines.dxf",
            blank_area=5000.0,
            volume_conservation_ratio=1.01,
            bend_count=2,
            metadata_={}
        )
        db_session.add(result)
        await db_session.flush()

        bend1 = BendRecord(
            result_id=result.id,
            bend_index=0,
            angle_degrees=90.0,
            direction="up",
            inside_radius=2.0,
            bend_allowance=3.5,
            flange_length_side_a=50.0,
            flange_length_side_b=30.0,
            nearest_cut_distance=10.0,
            bend_line_start={"x": 0, "y": 50},
            bend_line_end={"x": 100, "y": 50},
            metadata_={}
        )
        db_session.add(bend1)
        await db_session.commit()

        response = await client.get(f"/api/parts/{test_part.id}/unfold/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"]["bend_count"] == 2
        assert len(data["result"]["bends"]) == 1
        assert data["result"]["bends"][0]["angle_degrees"] == 90.0

    @pytest.mark.asyncio
    async def test_download_profile_requires_completed_job(
        self, client: AsyncClient, mock_token_validator, db_session: AsyncSession, test_user: User, test_part: Part
    ):
        job = UnfoldJob(
            part_id=test_part.id,
            k_factor=0.33,
            kerf=0.0,
            status=UnfoldJobStatus.PENDING
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.get(f"/api/parts/{test_part.id}/unfold/{job.id}/profile")
        assert response.status_code == 404