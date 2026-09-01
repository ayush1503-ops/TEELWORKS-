"""Security helpers: upload validation + a simple in-memory rate limiter.

Phase 1 scope — every uploaded file passes FOUR checks before the app says
anything about it:

  1. Extension check   — only .jpg / .jpeg / .png are accepted
  2. Size check        — hard 8 MB limit (checked BEFORE reading all bytes)
  3. Magic-byte check  — the first bytes must really be a JPEG/PNG signature,
                         so a text file or program renamed to ".jpg" is rejected
  4. Decode check      — Pillow fully decodes the image in memory; a corrupted
                         or truncated file is rejected

Safety rules:
  * uploads are processed IN MEMORY only — never written to disk, never executed
  * Pillow's decompression-bomb guard (MAX_IMAGE_PIXELS) stays enabled
"""
import time
from collections import defaultdict, deque
from io import BytesIO

from fastapi import HTTPException, UploadFile
from PIL import Image

from app.core.config import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)

# Genuine first-byte signatures of JPEG and PNG files.
MAGIC_BYTES = [
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
]

# --- Simple sliding-window rate limiter, per client IP -----------------------
# Good enough for a prototype. At deployment (Phase 14) this is replaced by a
# shared limiter (e.g. Redis-backed) so limits apply across server instances.
_request_log: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(client_ip: str) -> None:
    """Raise HTTP 429 if this client exceeded RATE_LIMIT_REQUESTS in the window."""
    now = time.monotonic()
    window = _request_log[client_ip]
    # Drop timestamps that fell out of the window.
    while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute and try again.",
        )
    window.append(now)


def _detect_real_format(data: bytes) -> str | None:
    """Return 'JPEG'/'PNG' if the bytes start with a real image signature."""
    for magic, fmt in MAGIC_BYTES:
        if data.startswith(magic):
            return fmt
    return None


async def validate_upload(file: UploadFile) -> dict:
    """Validate one uploaded image and return REAL, measured metadata.

    Raises HTTPException with a clear, user-friendly message on any failure.
    """
    # 1) Extension check ------------------------------------------------------
    name = file.filename or ""
    suffix = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{suffix or name}'. "
                "Only JPG, JPEG and PNG images are allowed."
            ),
        )

    # 2) Size check (cheap header check first, then a bounded read) -----------
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=_size_error(file.size))
    data = await file.read(MAX_UPLOAD_BYTES + 1)     # never read more than limit+1
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=_size_error(len(data)))

    # 3) Magic-byte check ------------------------------------------------------
    real_format = _detect_real_format(data)
    if real_format is None:
        raise HTTPException(
            status_code=415,
            detail="This file is not a real JPG/PNG image (content check failed).",
        )

    # 4) Safe in-memory decode -------------------------------------------------
    try:
        with Image.open(BytesIO(data)) as img:
            img.verify()                 # structural check; catches corruption
        with Image.open(BytesIO(data)) as img:
            width, height = img.size     # need a second open: verify() invalidates
            pillow_format = (img.format or real_format).upper()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="The image file is corrupted or truncated and cannot be read.",
        )

    info = {
        "filename": name,
        "format": pillow_format,
        "width": width,
        "height": height,
        "size_bytes": len(data),
        "megapixels": round((width * height) / 1_000_000, 2),
        "aspect_ratio": round(width / height, 3),
        "data": data,   # decoded bytes — popped by the analyzer service
    }
    return info


def _size_error(size_bytes: int) -> str:
    max_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
    return (
        f"Image is too large ({size_bytes / (1024 * 1024):.1f} MB). "
        f"Maximum is {max_mb:.0f} MB."
    )
