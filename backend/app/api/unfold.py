from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.auth import get_current_user, require_operator, require_viewer, CurrentUser
from app.db.session import get_db
from app.models.part import Part
from app.models.unfold import UnfoldJob, UnfoldResult, BendRecord, UnfoldJobStatus
from app.services.unfold_service import UnfoldService


router = APIRouter(prefix="/api/parts", tags=["unfold"])

unfold_service = UnfoldService()


class UnfoldRequest(BaseModel):
    k_factor: Optional[float] = Field(default=0.33, ge=0.0, le=1.0)
    bend_table: Optional[dict] = None
    kerf: float = Field(default=0.0, ge=0.0)


class UnfoldResponse(BaseModel):
    job_id: int
    status: str
    message: str


@router.post("/{part_id}/unfold", response_model=UnfoldResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_unfold(
    part_id: int,
    request: UnfoldRequest,
    current_user: CurrentUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    # Verify part ownership
    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    if part.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Part not ready for unfolding (status: {part.status})"
        )

    # Create job
    job = UnfoldJob(
        part_id=part.id,
        k_factor=request.k_factor,
        bend_table=request.bend_table,
        kerf=request.kerf,
        status=UnfoldJobStatus.PENDING
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Run unfold (in production, this would be a background task)
    try:
        await unfold_service.unfold_part(db, job, part)
    except Exception as e:
        # Error already handled in service
        pass

    return UnfoldResponse(
        job_id=job.id,
        status=job.status.value,
        message="Unfold job completed" if job.status == UnfoldJobStatus.COMPLETED else "Unfold job failed"
    )


@router.get("/{part_id}/unfold/{job_id}")
async def get_unfold_result(
    part_id: int,
    job_id: int,
    current_user: CurrentUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    # Verify part ownership
    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    # Get job
    result = await db.execute(
        select(UnfoldJob).where(UnfoldJob.id == job_id, UnfoldJob.part_id == part_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unfold job not found")

    response = {
        "job_id": job.id,
        "part_id": job.part_id,
        "status": job.status.value,
        "k_factor": job.k_factor,
        "kerf": job.kerf,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message
    }

    if job.result:
        result_obj = job.result
        bends_result = await db.execute(
            select(BendRecord).where(BendRecord.result_id == result_obj.id).order_by(BendRecord.bend_index)
        )
        bends = bends_result.scalars().all()

        response["result"] = {
            "profile_path": result_obj.profile_path,
            "bend_lines_path": result_obj.bend_lines_path,
            "blank_area": result_obj.blank_area,
            "volume_conservation_ratio": result_obj.volume_conservation_ratio,
            "bend_count": result_obj.bend_count,
            "metadata": result_obj.metadata_,
            "bends": [
                {
                    "bend_index": b.bend_index,
                    "angle_degrees": b.angle_degrees,
                    "direction": b.direction,
                    "inside_radius": b.inside_radius,
                    "bend_allowance": b.bend_allowance,
                    "flange_length_side_a": b.flange_length_side_a,
                    "flange_length_side_b": b.flange_length_side_b,
                    "nearest_cut_distance": b.nearest_cut_distance,
                    "bend_line_start": b.bend_line_start,
                    "bend_line_end": b.bend_line_end,
                    "metadata": b.metadata_
                }
                for b in bends
            ]
        }

    return response


@router.get("/{part_id}/unfold/{job_id}/profile")
async def download_unfold_profile(
    part_id: int,
    job_id: int,
    current_user: CurrentUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    from fastapi.responses import FileResponse
    import os

    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    result = await db.execute(
        select(UnfoldJob).where(UnfoldJob.id == job_id, UnfoldJob.part_id == part_id)
    )
    job = result.scalar_one_or_none()
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Unfold result not found")

    if not os.path.exists(job.result.profile_path):
        raise HTTPException(status_code=404, detail="Profile file not found")

    return FileResponse(
        job.result.profile_path,
        media_type="application/dxf",
        filename=f"unfold_{job_id}_profile.dxf"
    )


@router.get("/{part_id}/unfold/{job_id}/bendlines")
async def download_unfold_bendlines(
    part_id: int,
    job_id: int,
    current_user: CurrentUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    from fastapi.responses import FileResponse
    import os

    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")

    result = await db.execute(
        select(UnfoldJob).where(UnfoldJob.id == job_id, UnfoldJob.part_id == part_id)
    )
    job = result.scalar_one_or_none()
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Unfold result not found")

    if not os.path.exists(job.result.bend_lines_path):
        raise HTTPException(status_code=404, detail="Bend lines file not found")

    return FileResponse(
        job.result.bend_lines_path,
        media_type="application/dxf",
        filename=f"unfold_{job_id}_bendlines.dxf"
    )