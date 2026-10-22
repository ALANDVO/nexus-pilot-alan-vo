import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.config import get_settings
from app.core.auth import get_current_user, require_operator, require_viewer, CurrentUser
from app.db.session import get_db
from app.models.part import Part, PartStatus
from app.models.user import User
from app.services.cad_service import CadService


router = APIRouter(prefix="/api/parts", tags=["parts"])

cad_service = CadService()


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_part(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    settings = get_settings()

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in [".step", ".stp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only STEP files (.step, .stp) are supported"
        )

    # Save upload
    try:
        file_path, file_size = cad_service.save_upload(file.file, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))

    # Create part record
    part = Part(
        owner_id=current_user.user.id,
        filename=Path(file_path).name,
        original_filename=file.filename,
        content_type=file.content_type or "application/step",
        file_size=file_size,
        file_path=file_path,
        status=PartStatus.UPLOADED,
        metadata_={}
    )
    db.add(part)
    await db.commit()
    await db.refresh(part)

    # Try to get basic info
    try:
        solid = cad_service.load_solid(file_path)
        info = cad_service.get_solid_info(solid)
        part.metadata_ = info
        part.status = PartStatus.READY
        await db.commit()
        await db.refresh(part)
    except Exception as e:
        part.status = PartStatus.FAILED
        part.metadata_ = {"error": str(e)}
        await db.commit()

    return {
        "id": part.id,
        "filename": part.filename,
        "original_filename": part.original_filename,
        "file_size": part.file_size,
        "status": part.status.value,
        "metadata": part.metadata_,
        "created_at": part.created_at.isoformat()
    }


@router.get("")
async def list_parts(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    current_user: CurrentUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    query = select(Part).where(Part.owner_id == current_user.user.id)

    if status_filter:
        try:
            status_enum = PartStatus(status_filter)
            query = query.where(Part.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    query = query.order_by(Part.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    parts = result.scalars().all()

    return {
        "parts": [
            {
                "id": p.id,
                "filename": p.filename,
                "original_filename": p.original_filename,
                "file_size": p.file_size,
                "status": p.status.value,
                "metadata": p.metadata_,
                "created_at": p.created_at.isoformat()
            }
            for p in parts
        ],
        "skip": skip,
        "limit": limit
    }


@router.get("/{part_id}")
async def get_part(
    part_id: int,
    current_user: CurrentUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    return {
        "id": part.id,
        "filename": part.filename,
        "original_filename": part.original_filename,
        "file_size": part.file_size,
        "status": part.status.value,
        "metadata": part.metadata_,
        "created_at": part.created_at.isoformat(),
        "updated_at": part.updated_at.isoformat()
    }


@router.get("/{part_id}/download")
async def download_part(
    part_id: int,
    current_user: CurrentUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    if not os.path.exists(part.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(
        part.file_path,
        media_type="application/step",
        filename=part.original_filename
    )


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_part(
    part_id: int,
    current_user: CurrentUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Part).where(Part.id == part_id, Part.owner_id == current_user.user.id)
    )
    part = result.scalar_one_or_none()

    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    # Delete file
    try:
        os.unlink(part.file_path)
    except OSError:
        pass

    await db.delete(part)
    await db.commit()