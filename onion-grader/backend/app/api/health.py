"""GET /api/health — liveness probe + quick way to see which phase the build is on."""
from fastapi import APIRouter

from app.core.config import APP_NAME, APP_VERSION, CURRENT_PHASE

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "phase": CURRENT_PHASE,
    }
