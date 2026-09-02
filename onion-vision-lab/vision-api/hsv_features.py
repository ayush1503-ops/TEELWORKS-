"""Shared HSV / texture feature extraction for the Onion Vision Lab.

This module is the SINGLE source of truth for hand-crafted visual features.
It is used by:
  * condition.py            (rule-based visible-condition heuristic, Phase 1)
  * train/phase2 RF training (scikit-learn RandomForest features, Phase 2)
  * ensemble.py             (fused condition signals, Phase 2 serving)

Everything operates on BGR numpy images (OpenCV convention).
No ML here - pure measurement. Every number is computed from pixels.
"""

from __future__ import annotations

import numpy as np
import cv2

# Canonical feature ordering (must never change after training; version-stamped)
FEATURE_VERSION = "hsv_tex_v1"
FEATURE_NAMES = [
    "hue_mean", "hue_std", "sat_mean", "sat_std", "val_mean", "val_std",
    "dark_ratio", "very_dark_ratio", "green_ratio", "brown_ratio",
    "pale_ratio", "specular_ratio", "edge_density", "laplacian_var",
    "contrast_std", "sat_gradient",
] + [f"lbp_b{i}" for i in range(9)] + ["hue_entropy"]


def _resize_max(img: np.ndarray, max_side: int = 160) -> np.ndarray:
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def _lbp_bins(gray: np.ndarray) -> np.ndarray:
    """Uniform-ish Local Binary Pattern histogram (9 bins = number of 1-bits).

    Hand-rolled LBP so we do not depend on scikit-image.  8-neighbour sign
    pattern, binned by population count (0..8) and L1-normalised.
    """
    g = gray.astype(np.int16)
    rows, cols = g.shape
    if rows < 3 or cols < 3:
        return np.zeros(9, dtype=np.float32)
    center = g[1:-1, 1:-1]
    pattern = np.zeros((rows - 2, cols - 2), dtype=np.uint8)
    bit = 1
    for dy, dx in ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)):
        neighbor = g[1 + dy: rows - 1 + dy, 1 + dx: cols - 1 + dx]
        pattern |= (neighbor >= center).astype(np.uint8) * bit
        bit <<= 1
    # Bin by number of 1 bits (rotation-invariant population count)
    popcount = np.zeros((rows - 2, cols - 2), dtype=np.uint8)
    for b in range(8):
        popcount += (pattern >> b) & 1
    hist = np.bincount(popcount.ravel(), minlength=9).astype(np.float32)
    total = hist.sum()
    return hist / total if total > 0 else hist


def extract_features(bgr: np.ndarray) -> dict:
    """Measure the canonical feature dict on a BGR crop (onion candidate)."""
    img = _resize_max(bgr)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(np.float32), hsv[..., 1].astype(np.float32), hsv[..., 2].astype(np.float32)
    hue_deg = h * 2.0  # OpenCV hue 0..179 -> degrees 0..358

    dark_mask = (v < 70) & (s > 30)
    very_dark_mask = v < 45
    green_mask = (h >= 35) & (h <= 85) & (s > 40) & (v > 40)   # sprout / greens
    brown_mask = (h >= 2) & (h <= 22) & (s > 60) & (v > 60)    # healthy onion skin
    pale_mask = (s < 45) & (v > 120)                            # pale gash / dried skin
    specular_mask = (v > 215) & (s < 60)                        # shiny highlight

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(sobelx ** 2 + sobely ** 2)
    edge_density = float((mag > 60).mean())
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())

    sat_gradient = float(np.abs(np.diff(s, axis=0)).mean()) if s.shape[0] > 1 else 0.0

    # Hue entropy (in 18-degree bins) - mottled skin vs. uniform skin
    hist = np.bincount((hue_deg / 18.0).astype(np.intp).ravel(), minlength=20).astype(np.float64)
    p = hist / max(hist.sum(), 1)
    hue_entropy = float(-(p[p > 0] * np.log2(p[p > 0])).sum())

    feats = {
        "hue_mean": float(hue_deg.mean()), "hue_std": float(hue_deg.std()),
        "sat_mean": float(s.mean()), "sat_std": float(s.std()),
        "val_mean": float(v.mean()), "val_std": float(v.std()),
        "dark_ratio": float(dark_mask.mean()),
        "very_dark_ratio": float(very_dark_mask.mean()),
        "green_ratio": float(green_mask.mean()),
        "brown_ratio": float(brown_mask.mean()),
        "pale_ratio": float(pale_mask.mean()),
        "specular_ratio": float(specular_mask.mean()),
        "edge_density": edge_density,
        "laplacian_var": laplacian_var,
        "contrast_std": float(gray.std()),
        "sat_gradient": sat_gradient,
    }
    lbp = _lbp_bins(gray)
    for i, b in enumerate(lbp):
        feats[f"lbp_b{i}"] = float(b)
    feats["hue_entropy"] = hue_entropy
    return feats


def feature_vector(bgr: np.ndarray) -> np.ndarray:
    """Feature matrix row in canonical FEATURE_NAMES order."""
    f = extract_features(bgr)
    return np.array([f[name] for name in FEATURE_NAMES], dtype=np.float32)


# ---------------------------------------------------------------------------
# Phase-1 style visible-condition cues (kept as ONE of the three fused signals)
# ---------------------------------------------------------------------------

def condition_cues(bgr: np.ndarray) -> dict:
    """The Phase-1 heuristic cue set used by condition.py and the meta-learner.

    darkRatio : share of pixels that are dark AND coloured (blemish / mold-like)
    satStd    : saturation spread (mottled, uneven skin)
    greenTop  : share of green (sprout-coloured) pixels in the top quarter
    paleRatio : pale low-saturation patches (dried gash / skin damage)
    edgeDensity, laplacianVar : surface roughness cues
    """
    img = _resize_max(bgr)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0].astype(np.float32), hsv[..., 1].astype(np.float32), hsv[..., 2].astype(np.float32)
    dark_mask = (v < 70) & (s > 30)
    green_mask = (h >= 35) & (h <= 85) & (s > 40) & (v > 40)
    pale_mask = (s < 45) & (v > 120)

    top = max(1, int(img.shape[0] * 0.25))
    green_top = float(green_mask[:top, :].mean())

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(sobelx ** 2 + sobely ** 2)

    return {
        "darkRatio": float(dark_mask.mean()),
        "satStd": float(s.std()),
        "greenTop": green_top,
        "paleRatio": float(pale_mask.mean()),
        "edgeDensity": float((mag > 60).mean()),
        "laplacianVar": float(cv2.Laplacian(gray, cv2.CV_32F).var()),
    }
