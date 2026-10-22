from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.api.parts import router as parts_router
from app.api.unfold import router as unfold_router

__all__ = ["api_router", "auth_router", "parts_router", "unfold_router"]