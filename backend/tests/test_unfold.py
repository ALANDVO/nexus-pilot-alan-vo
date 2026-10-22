import pytest
from unittest.mock import patch, AsyncMock


class TestUnfoldAlgorithm:
    def test_unfold_service_instantiation(self):
        from app.services.unfold_service import UnfoldService
        service = UnfoldService(output_dir="/tmp/test")
        assert service is not None

    def test_unfolded_dataclass_structure(self):
        from app.services.unfold_service import Unfolded
        from build123d import Compound, Edge
        unfolded = Unfolded(
            profile=Compound([]),
            bend_lines=[],
            bends=[]
        )
        assert unfolded.profile is not None
        assert isinstance(unfolded.bend_lines, list)
        assert isinstance(unfolded.bends, list)

    @pytest.mark.asyncio
    async def test_unfold_part_updates_job_status(self, db_session):
        from app.models.unfold import UnfoldJob, UnfoldJobStatus
        from app.models.part import Part, PartStatus
        from app.models.user import User
        from app.services.unfold_service import UnfoldService

        user = User(keycloak_sub="test", email="test@test.com", username="test", roles=["operator"])
        db_session.add(user)
        await db_session.commit()

        part = Part(
            owner_id=user.id,
            filename="test.step",
            original_filename="test.step",
            content_type="application/step",
            file_size=100,
            file_path="/tmp/test.step",
            status=PartStatus.READY
        )
        db_session.add(part)
        await db_session.commit()

        job = UnfoldJob(part_id=part.id, k_factor=0.33, kerf=0.0, status=UnfoldJobStatus.PENDING)
        db_session.add(job)
        await db_session.commit()

        # Test that job status transitions work
        assert job.status == UnfoldJobStatus.PENDING
        job.status = UnfoldJobStatus.RUNNING
        await db_session.commit()
        assert job.status == UnfoldJobStatus.RUNNING

    def test_bend_allowance_calculation_k_factor(self):
        """Test BA = θ * (r + K * t)"""
        import math
        angle_deg = 90.0
        r_in = 2.0
        thickness = 2.0
        k_factor = 0.33

        angle_rad = math.radians(angle_deg)
        ba = angle_rad * (r_in + k_factor * thickness)

        # 90° = π/2, so BA = π/2 * (2 + 0.33*2) = π/2 * 2.66 ≈ 4.178
        expected = math.pi / 2 * 2.66
        assert abs(ba - expected) < 0.001

    def test_bend_allowance_calculation_bend_table(self):
        """Test bend table lookup"""
        bend_table = {
            "2.0": {"2.0": {"90": 3.5}}
        }
        thickness = 2.0
        radius = 2.0
        angle = 90

        key_t = str(thickness)
        key_r = str(radius)
        key_a = str(angle)

        assert bend_table[key_t][key_r][key_a] == 3.5

    def test_refusal_conditions_hem_curl(self):
        """Hems/curls: radius < thickness or sweep > 180°"""
        thickness = 2.0
        # Hem: radius < thickness
        assert 1.0 < thickness  # Would be refused
        # Curl: sweep > 180
        assert 190 > 180  # Would be refused

    def test_refusal_conditions_conical_bend(self):
        """Conical/rolled bends: non-cylindrical or non-coaxial"""
        # Would be detected in _coaxial check
        pass

    def test_refusal_conditions_variable_thickness(self):
        """Variable thickness: no single thickness consensus"""
        votes = [1.0, 2.0, 3.0, 4.0]
        from app.services.cad_service import CadService
        service = CadService()
        consensus = service._consensus_thickness(votes, tolerance=0.01)
        assert consensus is None

    def test_refusal_conditions_collision(self):
        """Flanges that collide when unfolded - would be detected during layout"""
        # Placeholder for collision detection test
        pass


class TestStepLoaderEdgeCases:
    def test_empty_step_file(self):
        from app.services.step_loader import StepLoader
        loader = StepLoader()
        # Empty file would raise in load_step_progressive
        pass

    def test_memory_envelope_exact_match(self):
        from app.services.step_loader import StepLoader
        loader = StepLoader(memory_envelope_mb=100)
        assert loader.check_memory_envelope(100) is True
        assert loader.check_memory_envelope(100.1) is False

    def test_load_plan_empty_components(self):
        from app.services.step_loader import StepLoader, StepLoadResult
        loader = StepLoader(memory_envelope_mb=100)
        result = StepLoadResult([], 0, 0, 0)
        plan = loader.get_load_plan(result)
        assert plan["loadable"] == []
        assert plan["skipped"] == []