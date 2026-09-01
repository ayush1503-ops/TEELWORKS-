"""LAYER A — OpenCV preprocessing & onion detection.

Pipeline (every step exists for a stated reason):

    load (PIL, EXIF-rotated)          phones store rotated JPEGs; orient first
      → resize (max side 1024)          same scale for every photo, faster
      → Gaussian blur (5×5)             kill sensor noise/dust before thresholds
      → BGR→HSV                         separate colour (Hue) from lighting (Value)
      → segmentation (3 candidate masks) onions vary: red/pink/yellow/white skins
      → morphology (open/close)          speckles out, holes filled
      → largest solid contour           THE onion
      → feature extraction (features.py)

Three candidate masks are tried because no single threshold works everywhere:
  1. chroma mask   — saturated + bright pixels (coloured onions on pale tables)
  2. Otsu on Sat   — adapts to the actual image's saturation distribution
  3. Otsu on Gray⁻¹ — darker object on lighter background (white onions too)
The most plausible candidate (solid, 2–92% of the frame) wins. If none is
plausible we honestly report "no onion detected" + capture guidance.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 1024


# --------------------------------------------------------------------- #
# Data types                                                            #
# --------------------------------------------------------------------- #
@dataclass
class DetectionResult:
    found: bool = False
    reason: str = ""
    image: np.ndarray | None = None          # working BGR image (resized)
    mask: np.ndarray | None = None           # uint8 {0,255}
    contour: np.ndarray | None = None        # largest contour
    bbox: tuple[int, int, int, int] | None = None   # x, y, w, h
    area_fraction: float = 0.0               # onion area / image area
    solidity: float = 0.0                    # contour area / convex-hull area
    method: str = ""                         # which candidate mask won


# --------------------------------------------------------------------- #
# Loading & resizing                                                    #
# --------------------------------------------------------------------- #
def load_bgr(data: bytes) -> np.ndarray | None:
    """Decode uploaded bytes → BDR image. PIL applies EXIF orientation."""
    try:
        pil = Image.open(io.BytesIO(data))
        pil = ImageOps.exif_transpose(pil).convert("RGB")
        return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def resize_max(img: np.ndarray, max_side: int = MAX_SIDE) -> np.ndarray:
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


# --------------------------------------------------------------------- #
# Segmentation                                                          #
# --------------------------------------------------------------------- #
def _clean(mask: np.ndarray) -> np.ndarray:
    """Morphological open (remove speckles) then close (fill pinholes)."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    m = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=2)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=3)
    return m


def _largest_component(mask: np.ndarray):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, 0.0, 0.0
    c = max(cnts, key=cv2.contourArea)
    area = float(cv2.contourArea(c))
    hull_area = float(cv2.contourArea(cv2.convexHull(c)))
    solidity = area / hull_area if hull_area > 0 else 0.0
    return c, area, solidity


def segment_onion(img_bgr: np.ndarray, rules: dict) -> DetectionResult:
    min_frac = float(rules.get("analysis", {}).get("min_onion_area_fraction", 0.02))
    max_frac = float(rules.get("analysis", {}).get("max_onion_area_fraction", 0.92))

    resized = resize_max(img_bgr)
    blurred = cv2.GaussianBlur(resized, (5, 5), 0)

    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    sat, val = hsv[:, :, 1], hsv[:, :, 2]
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)

    # Three candidate masks — see module docstring for why.
    candidates: dict[str, np.ndarray] = {
        "chroma_mask": ((sat > 55) & (val > 45)).astype(np.uint8) * 255,
    }
    _, sat_otsu = cv2.threshold(sat, 0, 255, cv2.THRESH_OTSU)
    candidates["saturation_otsu"] = sat_otsu
    candidates["gray_otsu_inv"] = cv2.threshold(
        gray, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV
    )[1]

    img_area = resized.shape[0] * resized.shape[1]
    best: tuple[float, str, np.ndarray, np.ndarray, float, float] | None = None

    for name, raw_mask in candidates.items():
        m = _clean(raw_mask)
        c, area, solidity = _largest_component(m)
        if c is None or area <= 0:
            continue
        frac = area / img_area
        if not (min_frac <= frac <= max_frac):
            continue                       # implausible: too small / whole frame
        # Prefer solid blobs of a sensible size (≈20% of frame is typical).
        score = solidity + (1.0 - abs(0.20 - frac))
        if best is None or score > best[0]:
            best = (score, name, m, c, frac, solidity)

    if best is None:
        return DetectionResult(
            found=False,
            reason=(
                "No onion-like region could be separated from the background. "
                "Retake guidance: place ONE onion on a plain, contrasting "
                "surface, centre it, and use even lighting."
            ),
            image=resized,
        )

    _, name, mask, contour, frac, sol = best
    x, y, w, h = cv2.boundingRect(contour)
    return DetectionResult(
        found=True,
        image=resized,
        mask=mask,
        contour=contour,
        bbox=(x, y, w, h),
        area_fraction=round(frac, 4),
        solidity=round(sol, 4),
        method=name,
    )


# --------------------------------------------------------------------- #
# Visualisation (explainability step 1: show WHAT was analysed)          #
# --------------------------------------------------------------------- #
def draw_annotations(
    det: DetectionResult,
    spots: list[tuple[int, int, int, int, float]] | None = None,
    sprout_band: tuple[int, int, int, int] | None = None,
) -> np.ndarray:
    """Return a copy with onion outline, bounding box, defect regions drawn."""
    if det.image is None:
        raise ValueError("no image")
    canvas = det.image.copy()

    if det.mask is not None:                      # faint green onion overlay
        overlay = canvas.copy()
        overlay[det.mask > 0] = (60, 200, 90)
        canvas = cv2.addWeighted(overlay, 0.18, canvas, 0.82, 0)

    if det.contour is not None:                   # thick outline
        cv2.drawContours(canvas, [det.contour], -1, (40, 180, 60), 3)

    if det.bbox is not None:                      # amber bounding box
        x, y, w, h = det.bbox
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (30, 160, 255), 2)
        cv2.putText(canvas, "onion", (x, max(14, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 160, 255), 2)

    if sprout_band is not None:                   # dashed-ish green band (sprout zone)
        x, y, w, h = sprout_band
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (80, 220, 120), 2)
        cv2.putText(canvas, "sprout zone", (x, max(14, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 220, 120), 2)

    for (sx, sy, sw, sh, _area) in spots or []:   # red defect regions
        cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), (60, 60, 255), 2)

    return canvas


def to_jpeg_b64(img: np.ndarray, quality: int = 85, max_side: int = 900) -> str:
    """Encode an OpenCV BGR image as a base64 JPEG data-URI payload."""
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return base64.b64encode(buf.tobytes()).decode("ascii")


# --------------------------------------------------------------------- #
# MULTI-ONION DETECTION (pile scanning)                                  #
# --------------------------------------------------------------------- #
def _candidate_masks(blurred: np.ndarray) -> dict[str, np.ndarray]:
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    sat, val = hsv[:, :, 1], hsv[:, :, 2]
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    _, sat_otsu = cv2.threshold(sat, 0, 255, cv2.THRESH_OTSU)
    return {
        "chroma": ((sat > 55) & (val > 45)).astype(np.uint8) * 255,
        "sat_otsu": sat_otsu,
        "gray_otsu_inv": cv2.threshold(
            gray, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY_INV)[1],
    }


def segment_onions_multi(img_bgr: np.ndarray, rules: dict,
                         max_count: int = 120) -> tuple[list[DetectionResult], str]:
    """Detect MANY onions in one photo (piles, jute bags, sorting tables).

    Candidate foreground mask (best of 3 methods by plausible blob count)
    → per-component distance transform → sure foreground seeds → WATERSHED
    to split touching onions → per-instance mask/contour/bbox.

    Honesty: heavily occluded or merged onions can still be missed/undercounted
    — the response says so. Returns (instances, method_name).
    """
    an = rules.get("analysis", {})
    min_frac = float(an.get("min_onion_area_fraction", 0.02))
    max_frac = float(an.get("max_onion_area_fraction", 0.92))
    pile_min = max(0.003, min_frac * 0.25)      # piles: allow smaller individuals

    resized = resize_max(img_bgr, 1280)          # more px → small onions visible
    blurred = cv2.GaussianBlur(resized, (5, 5), 0)
    img_area = resized.shape[0] * resized.shape[1]
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    best_name, fg, best_count = "none", None, 0
    for name, raw in _candidate_masks(blurred).items():
        m = _clean(raw)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        n_plausible = sum(1 for c in cnts
                          if pile_min <= cv2.contourArea(c) / img_area <= max_frac)
        if n_plausible > best_count:
            best_name, fg, best_count = name, m, n_plausible
    if fg is None or fg.sum() == 0:
        return [], "none"

    sure_bg = cv2.dilate(fg, k5, 3)
    dist = cv2.distanceTransform(fg, cv2.DIST_L2, 5)
    sure_fg = np.zeros_like(fg)
    n_comp, lbl = cv2.connectedComponents(fg)
    for ci in range(1, n_comp):
        comp = lbl == ci
        d = dist * comp
        mx = float(d.max())
        if mx > 12:
            sure_fg |= (d > 0.55 * mx).astype(np.uint8) * 255
        else:
            sure_fg |= comp.astype(np.uint8) * 255
    unknown = cv2.subtract(sure_bg, sure_fg)
    _n_mk, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown > 0] = 0
    markers = markers.astype(np.int32)
    cv2.watershed(resized.copy(), markers)

    out: list[DetectionResult] = []
    for lab in range(2, int(markers.max()) + 1):
        region = ((markers == lab) & (fg > 0)).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        area = float(cv2.contourArea(c))
        frac = area / img_area
        if frac < pile_min or frac > max_frac:
            continue
        hull_area = float(cv2.contourArea(cv2.convexHull(c)))
        solidity = area / hull_area if hull_area > 0 else 0.0
        mask = np.zeros(region.shape, np.uint8)
        cv2.drawContours(mask, [c], -1, 255, -1)
        x, y, w, h = cv2.boundingRect(c)
        out.append(DetectionResult(found=True, image=resized, mask=mask, contour=c,
                                   bbox=(x, y, w, h), area_fraction=round(frac, 4),
                                   solidity=round(solidity, 4), method="watershed"))
    out.sort(key=lambda d: -d.area_fraction)
    return out[:max_count], f"watershed+{best_name}"
