"""POST /api/scan — one photo of MANY onions → colour-coded instances + report."""
from fastapi import APIRouter, File, Request, UploadFile

from app.core.security import enforce_rate_limit, validate_upload
from app.services.scan import run_scan

router = APIRouter(tags=["scan"])


@router.post("/scan", summary="Scan a pile of onions (multi-onion detection + colour coding)")
async def scan(request: Request, file: UploadFile = File(...)) -> dict:
    enforce_rate_limit(request.client.host if request.client else "unknown")
    info = await validate_upload(file)          # same security checks as everywhere
    data = info.pop("data")
    return run_scan(data, info["filename"])
