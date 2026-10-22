from fastapi import APIRouter, Depends
from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "nexus-pilot-api",
        "version": "1.0.0",
        "environment": settings.env
    }


@router.get("/")
async def root():
    return {
        "name": "nexus-pilot-alan-vo",
        "description": "Give your agent CAD superpowers",
        "version": "1.0.0",
        "docs": "/docs"
    }