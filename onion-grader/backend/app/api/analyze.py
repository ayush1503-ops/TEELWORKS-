"""POST /api/analyze — the full honest pipeline for ONE onion image."""
from fastapi import APIRouter, File, Request, UploadFile

from app.core.security import enforce_rate_limit
from app.services.analyzer import analyze_image

router = APIRouter(tags=["analysis"])


@router.post("/analyze", summary="Analyze one onion image (OpenCV → rules → score → grade)")
async def analyze_onion(request: Request, file: UploadFile = File(...)) -> dict:
    enforce_rate_limit(request.client.host if request.client else "unknown")
    return await analyze_image(file)
