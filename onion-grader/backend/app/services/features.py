"""LAYER A (cont.) — turn the detected onion into MEASURED FACTS.

Every number produced here is directly computed from pixels — nothing is
estimated beyond what the image supports. These measurements feed:
  * the rule-based defect detector (defects.py)
  * the ML classifier (classifier.py / train_baseline.py) — SAME features,
    so the model stays explainable (feature importances)
  * the transparent quality score (scoring.py)

FEATURE_ORDER is the single source of truth for the ML feature vector —
used by both training and inference so they can never drift apart.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import cv2
import numpy as np

from app.services.preprocessing import DetectionResult

FEATURE_ORDER = [
    # geometry
    "circularity", "aspect_ratio", "solidity", "area_fraction",
    "equivalent_diameter_px",
    # colour
    "sat_mean", "sat_std", "val_mean", "val_std",
    "hue_circ_mean_deg", "hue_circular_std_deg", "hue_entropy", "specular_ratio",
    # defect evidence
    "dark_region_ratio", "dark_spot_count", "largest_spot_ratio",
    "green_top_ratio", "edge_density", "bright_region_ratio", "grad_mean",
]


@dataclass
class OnionFeatures:
    # --- geometry (pixels — mm requires calibration, stated openly) ---
    area_px: float = 0.0
    perimeter_px: float = 0.0
    bbox: tuple = (0, 0, 0, 0)
    width_px: int = 0
    height_px: int = 0
    equivalent_diameter_px: float = 0.0     # diameter of a circle with same area
    area_fraction: float = 0.0              # share of the photo occupied
    circularity: float = 0.0                # 4πA/P² — 1.0 = perfect circle
    aspect_ratio: float = 1.0
    solidity: float = 0.0                   # area / convex-hull area
    # --- colour (HSV statistics inside the onion) ---
    hue_circ_mean_deg: float = 0.0          # circular mean (red wraps 0/360!)
    hue_circular_std_deg: float = 0.0       # colour uniformity measure
    hue_entropy: float = 0.0                # colour diversity (bits) — two-tone skins
    sat_mean: float = 0.0
    sat_std: float = 0.0
    val_mean: float = 0.0
    val_std: float = 0.0
    specular_ratio: float = 0.0             # shiny highlights (wet rot / waxy skin)
    # --- defect evidence ---
    dark_region_ratio: float = 0.0          # dark pixels / onion pixels
    dark_spot_count: int = 0                # distinct dark blobs
    largest_spot_ratio: float = 0.0         # biggest blob / onion area
    bright_region_ratio: float = 0.0        # pale exposed flesh (cuts/gashes)
    grad_mean: float = 0.0                  # mean gradient magnitude (texture energy)
    spot_boxes: list = None                 # (x,y,w,h,area) for annotation
    green_top_ratio: float = 0.0            # green pixels in the neck band
    edge_density: float = 0.0               # Canny edges inside the skin
    # --- capture quality (drives honest analysis confidence) ---
    lighting_poor: bool = False
    shadow_risk: bool = False

    def dict(self) -> dict:
        d = asdict(self)
        d.pop("spot_boxes", None)           # internal detail, not for JSON
        return d

    def vector(self) -> list[float]:
        """ML feature vector — order fixed by FEATURE_ORDER."""
        return [float(getattr(self, k, 0.0) or 0.0) for k in FEATURE_ORDER]


def _circular_hue_stats(hue_opencv: np.ndarray) -> tuple[float, float]:
    """Mean/std of hue on a circle — red sits at both 0° and 360°, so a naive
    average of red onions (~10° and ~350°) would wrongly say ~180° (cyan!)."""
    if hue_opencv.size < 30:
        return 0.0, 0.0
    ang = np.deg2rad(hue_opencv.astype(np.float64) * 2.0)   # OpenCV H∈[0,179] → deg
    s, c = np.sin(ang), np.cos(ang)
    r = math.hypot(s.mean(), c.mean())
    mean_deg = math.degrees(math.atan2(s.mean(), c.mean())) % 360.0
    if r >= 1.0:
        std_deg = 0.0
    else:
        std_deg = math.degrees(math.sqrt(-2.0 * math.log(r)))
    return round(mean_deg, 1), round(min(std_deg, 180.0), 1)


def _hue_entropy(hue_opencv: np.ndarray) -> float:
    """Shannon entropy (bits) of the hue histogram inside the onion."""
    if hue_opencv.size < 30:
        return 0.0
    hist = np.bincount(hue_opencv.ravel(), minlength=180).astype(np.float64)
    p = hist / hist.sum()
    p = p[p > 0]
    return round(float(-(p * np.log2(p)).sum()), 2)


def extract_features(det: DetectionResult, rules: dict) -> OnionFeatures:
    f = OnionFeatures()
    img = det.image
    if not det.found or img is None or det.contour is None or det.mask is None:
        return f

    an = rules.get("analysis", {})
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    mask = det.mask > 0

    # ---------- geometry ----------
    f.area_px = round(float(cv2.contourArea(det.contour)), 1)
    f.perimeter_px = round(float(cv2.arcLength(det.contour, True)), 1)
    x, y, w, h = det.bbox
    f.bbox, f.width_px, f.height_px = (x, y, w, h), int(w), int(h)
    f.equivalent_diameter_px = round(math.sqrt(4.0 * f.area_px / math.pi), 1)
    f.area_fraction = det.area_fraction
    f.circularity = round(
        min(1.0, (4.0 * math.pi * f.area_px) / (f.perimeter_px ** 2)) if f.perimeter_px else 0.0, 4
    )
    f.aspect_ratio = round(w / h, 3) if h else 1.0
    f.solidity = det.solidity

    # ---------- colour ----------
    skin = mask & (sat > 40)                    # ignore pale/background-ish px
    f.hue_circ_mean_deg, f.hue_circular_std_deg = _circular_hue_stats(hue[skin])
    f.hue_entropy = _hue_entropy(hue[skin])
    f.sat_mean = round(float(sat[mask].mean()), 1) if mask.any() else 0.0
    f.sat_std = round(float(sat[mask].std()), 1) if mask.any() else 0.0
    f.val_mean = round(float(val[mask].mean()), 1) if mask.any() else 0.0
    f.val_std = round(float(val[mask].std()), 1) if mask.any() else 0.0
    f.specular_ratio = round(float(((val > 235) & (sat < 90) & mask).sum())
                             / max(1, int(mask.sum())), 4)

    # ---------- dark regions (rot / bruise evidence) ----------
    # Adaptive threshold: 'dark' means dark RELATIVE to this onion's own
    # brightness → tolerates different lighting conditions.
    v_in = val[mask]
    dark_thr = max(40.0, 0.55 * float(v_in.mean())) if v_in.size else 40.0
    dark_mask = ((val < dark_thr) & mask).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, k)
    onion_px = max(1, int(mask.sum()))
    f.dark_region_ratio = round(float((dark_mask > 0).sum()) / onion_px, 4)

    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(dark_mask, 8)
    min_blob = max(20.0, 0.0005 * onion_px)
    blobs = [tuple(map(int, stats[i][:4])) + (float(stats[i, 4]),)
             for i in range(1, n) if stats[i, 4] >= min_blob]
    blobs.sort(key=lambda b: -b[4])
    f.spot_boxes = blobs[:12]
    f.dark_spot_count = len(blobs)
    f.largest_spot_ratio = round(blobs[0][4] / onion_px, 4) if blobs else 0.0

    # pale gashes/cuts: flesh exposed by damage is BRIGHTER & less saturated
    bright_thr = min(240.0, 1.28 * float(v_in.mean())) if v_in.size else 240.0
    f.bright_region_ratio = round(float(((val > bright_thr) & (sat < 130) & mask).sum())
                                  / onion_px, 4)

    # ---------- sprouting (green shoots at the neck) ----------
    band_top = max(0, y - int(0.10 * h))
    band = np.zeros_like(mask)
    band[band_top:y + int(0.38 * h), x:x + w] = True
    band_px = band & mask
    green = (hue >= 35) & (hue <= 90) & (sat > 60) & (val > 50)
    denom = max(1, int(band_px.sum()))
    f.green_top_ratio = round(float((green & band_px).sum()) / denom, 4)

    # ---------- skin condition (edge texture inside the onion) ----------
    inner = cv2.erode(det.mask, k, iterations=3)   # avoid the silhouette edge
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 64, 160)
    inner_px = max(1, int((inner > 0).sum()))
    f.edge_density = round(float((edges & (inner > 0)).sum()) / inner_px, 4)

    # gradient energy inside the onion (cuts & cracks raise it, blur lowers it)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    f.grad_mean = round(float(cv2.magnitude(gx, gy)[mask].mean()), 1)

    # ---------- capture quality ----------
    f.lighting_poor = float(val.mean()) < float(an.get("poor_lighting_mean_value", 60))
    bg = val[~cv2.dilate(det.mask, np.ones((25, 25), np.uint8)).astype(bool)]
    f.shadow_risk = bool(bg.size > 50 and float(bg.std()) > float(an.get("shadow_risk_bg_std", 55)))

    return f


def sprout_band_bbox(det: DetectionResult) -> tuple[int, int, int, int] | None:
    """The neck region we scan for green shoots (used for annotation)."""
    if not det.found or det.bbox is None:
        return None
    x, y, w, h = det.bbox
    return (x, max(0, y - int(0.10 * h)), w, int(0.48 * h))
