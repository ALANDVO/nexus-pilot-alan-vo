import os
import uuid
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from build123d import Shape, Compound, export_step, Edge, Face, Wire, Location, Vector, ExportDXF

from app.services.cad_service import CadService
from app.models.unfold import UnfoldJob, UnfoldResult, BendRecord, UnfoldJobStatus
from app.models.part import Part
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@dataclass
class Unfolded:
    profile: Compound
    bend_lines: list[Edge]
    bends: list[dict]


class UnfoldService:
    def __init__(self, output_dir: str = "./data/unfolds"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cad_service = CadService()

    async def unfold_part(
        self,
        db: AsyncSession,
        job: UnfoldJob,
        part: Part
    ) -> UnfoldResult:
        job.status = UnfoldJobStatus.RUNNING
        await db.commit()

        try:
            solid = self.cad_service.load_solid(part.file_path)
            thickness, bends = self.cad_service.validate_sheet_metal(solid)

            # Use K-factor or bend table
            k_factor = job.k_factor or 0.33
            kerf = job.kerf or 0.0

            unfolded = self._unfold_solid(solid, thickness, bends, k_factor, kerf)

            # Save outputs
            job_id_str = f"{job.id:06d}"
            profile_path = self.output_dir / f"{job_id_str}_profile.dxf"
            bend_lines_path = self.output_dir / f"{job_id_str}_bendlines.dxf"

            ExportDXF(unfolded.profile).save(str(profile_path))
            if unfolded.bend_lines:
                compound_bl = Compound(unfolded.bend_lines)
                ExportDXF(compound_bl).save(str(bend_lines_path))
            else:
                # Create empty DXF
                ExportDXF(Compound([])).save(str(bend_lines_path))

            # Calculate metrics
            blank_area = unfolded.profile.area
            volume = solid.volume
            volume_conservation = volume / (thickness * blank_area) if blank_area > 0 else 0.0

            # Create result
            result = UnfoldResult(
                job_id=job.id,
                profile_path=str(profile_path),
                bend_lines_path=str(bend_lines_path),
                blank_area=blank_area,
                volume_conservation_ratio=volume_conservation,
                bend_count=len(unfolded.bends),
                metadata_={
                    "thickness": thickness,
                    "k_factor": k_factor,
                    "kerf": kerf,
                    "solid_volume": volume
                }
            )
            db.add(result)
            await db.flush()

            # Create bend records
            for i, bend_data in enumerate(unfolded.bends):
                bend_record = BendRecord(
                    result_id=result.id,
                    bend_index=i,
                    angle_degrees=bend_data["angle_degrees"],
                    direction=bend_data["direction"],
                    inside_radius=bend_data["inside_radius"],
                    bend_allowance=bend_data["bend_allowance"],
                    flange_length_side_a=bend_data["flange_length_side_a"],
                    flange_length_side_b=bend_data["flange_length_side_b"],
                    nearest_cut_distance=bend_data["nearest_cut_distance"],
                    bend_line_start=bend_data["bend_line_start"],
                    bend_line_end=bend_data["bend_line_end"],
                    metadata_=bend_data.get("metadata_", {})
                )
                db.add(bend_record)

            job.status = UnfoldJobStatus.COMPLETED
            job.result_id = result.id
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(result)
            return result

        except Exception as e:
            job.status = UnfoldJobStatus.FAILED
            job.error_message = str(e)
            await db.commit()
            raise

    def _unfold_solid(
        self,
        solid: Shape,
        thickness: float,
        bends: list[dict],
        k_factor: float,
        kerf: float
    ) -> Unfolded:
        """
        Core unfolding algorithm:
        1. Build flange tree from planar faces connected by bends
        2. Root at largest flange, lay flat by composing rotations about bend axes
        3. Replace each cylindrical bend with flat strip of width BA = θ*(r + K*t)
        4. Union all flanges and bend strips, offset for kerf
        5. Generate bend lines on the flat pattern
        """
        # This is a skeleton implementation - the full algorithm would:
        # - Use build123d/OCC to traverse topology
        # - Build adjacency graph of faces
        # - Identify flange faces (planar) and bend faces (cylindrical)
        # - Compute transformation matrices for each flange to XY plane
        # - Apply bend allowance compensation
        # - Fuse and kerf-offset

        # For now, return a minimal valid structure for testing
        # In real implementation, this would be the full algorithm per issue #614

        # Placeholder: create a simple rectangular profile as proxy
        from build123d import Rectangle, extrude, Plane
        profile = Rectangle(100, 50).extrude(thickness)  # Dummy
        profile = Compound([profile])

        # Placeholder bend lines
        bend_lines = []
        bend_records = []

        for i, bend in enumerate(bends):
            angle_rad = bend["angle_degrees"] * 3.14159 / 180
            r_in = bend["inside_radius"]
            ba = angle_rad * (r_in + k_factor * thickness)

            bend_records.append({
                "angle_degrees": bend["angle_degrees"],
                "direction": bend["direction"],
                "inside_radius": r_in,
                "bend_allowance": ba,
                "flange_length_side_a": 50.0,  # Placeholder
                "flange_length_side_b": 50.0,  # Placeholder
                "nearest_cut_distance": 10.0,  # Placeholder
                "bend_line_start": {"x": 0.0, "y": 50.0 + i * 10},
                "bend_line_end": {"x": 100.0, "y": 50.0 + i * 10},
                "metadata_": {}
            })

            # Create bend line edge
            from build123d import Line
            bend_lines.append(Line(
                Vector(0, 50.0 + i * 10, 0),
                Vector(100.0, 50.0 + i * 10, 0)
            ).edge())

        return Unfolded(
            profile=profile,
            bend_lines=bend_lines,
            bends=bend_records
        )

    async def get_result(self, db: AsyncSession, job_id: int) -> Optional[UnfoldResult]:
        result = await db.execute(
            select(UnfoldResult).where(UnfoldResult.job_id == job_id)
        )
        return result.scalar_one_or_none()


from datetime import datetime, timezone