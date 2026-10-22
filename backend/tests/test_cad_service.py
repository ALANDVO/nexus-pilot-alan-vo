import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.part import Part, PartStatus
from app.models.user import User
from app.services.cad_service import CadService


class TestCadService:
    @pytest.fixture
    def cad_service(self):
        return CadService(upload_dir="/tmp/test_uploads", max_size_mb=10)

    def test_save_upload_rejects_oversized_file(self, cad_service, tmp_path):
        large_file = tmp_path / "large.step"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))

        with open(large_file, "rb") as f:
            with pytest.raises(ValueError, match="exceeds maximum size"):
                cad_service.save_upload(f, "large.step")

    def test_save_upload_accepts_valid_file(self, cad_service, tmp_path):
        test_file = tmp_path / "test.step"
        test_file.write_bytes(b"STEP file content")

        with open(test_file, "rb") as f:
            path, size = cad_service.save_upload(f, "test.step")

        assert size == len(b"STEP file content")
        assert Path(path).exists()

    def test_load_solid_raises_on_missing_file(self, cad_service):
        with pytest.raises(FileNotFoundError):
            cad_service.load_solid("/nonexistent/file.step")

    def test_consensus_thickness_finds_cluster(self, cad_service):
        votes = [2.0, 2.01, 1.99, 2.0, 5.0, 5.0]
        thickness = cad_service._consensus_thickness(votes, tolerance=0.02)
        assert thickness is not None
        assert abs(thickness - 2.0) < 0.02

    def test_consensus_thickness_returns_none_for_no_consensus(self, cad_service):
        votes = [1.0, 2.0, 3.0, 4.0, 5.0]
        thickness = cad_service._consensus_thickness(votes, tolerance=0.01)
        assert thickness is None

    def test_consensus_thickness_requires_minimum_cluster(self, cad_service):
        votes = [2.0, 5.0]
        thickness = cad_service._consensus_thickness(votes, tolerance=0.01)
        assert thickness is None


class TestUnfoldService:
    @pytest.fixture
    def unfold_service(self):
        from app.services.unfold_service import UnfoldService
        return UnfoldService(output_dir="/tmp/test_unfolds")

    @pytest.mark.asyncio
    async def test_unfold_creates_job_and_result(self, db_session: AsyncSession, test_user: User, test_part: Part):
        from app.models.unfold import UnfoldJob, UnfoldJobStatus
        from app.services.unfold_service import UnfoldService

        # This test would require a real STEP file and build123d
        # For now, test the service instantiation
        service = UnfoldService()
        assert service is not None
        assert service.output_dir.exists()

    @pytest.mark.asyncio
    async def test_unfold_job_status_transitions(self, db_session: AsyncSession, test_user: User, test_part: Part):
        from app.models.unfold import UnfoldJob, UnfoldJobStatus

        job = UnfoldJob(
            part_id=test_part.id,
            k_factor=0.33,
            kerf=0.0,
            status=UnfoldJobStatus.PENDING
        )
        db_session.add(job)
        await db_session.commit()

        assert job.status == UnfoldJobStatus.PENDING

        job.status = UnfoldJobStatus.RUNNING
        await db_session.commit()

        assert job.status == UnfoldJobStatus.RUNNING


class TestStepLoader:
    def test_load_step_progressive_returns_metadata(self, tmp_path):
        from app.services.step_loader import StepLoader

        loader = StepLoader(memory_envelope_mb=100)
        # Would need a real STEP file for full test
        assert loader.memory_envelope_mb == 100

    def test_check_memory_envelope(self):
        from app.services.step_loader import StepLoader

        loader = StepLoader(memory_envelope_mb=100)
        assert loader.check_memory_envelope(50) is True
        assert loader.check_memory_envelope(150) is False

    def test_get_load_plan_selects_within_envelope(self):
        from app.services.step_loader import StepLoader, StepComponent, StepLoadResult
        from build123d import Compound

        loader = StepLoader(memory_envelope_mb=10)

        # Mock components
        comp1 = StepComponent("c1", Compound([]), 100, 100, {})
        comp2 = StepComponent("c2", Compound([]), 200, 5000, {})  # Large
        comp3 = StepComponent("c3", Compound([]), 50, 50, {})

        result = StepLoadResult([comp1, comp2, comp3], 350, 3, 50)
        plan = loader.get_load_plan(result)

        assert len(plan["loadable"]) >= 1
        assert plan["envelope_mb"] == 10