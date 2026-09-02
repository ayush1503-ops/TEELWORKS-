"""Visible-condition analysis for a single onion crop (Phase 1 heuristic).

Rules operate ONLY on measurable pixels. It never claims to see inside the
onion, never invents findings, and limits itself to the allowed finding
vocabulary:

    Surface Discoloration / Surface Damage / Possible Mold-Like Growth /
    Shriveling / Sprouting

In Phase 2 this heuristic is ONE of three fused signals (see ensemble.py):
CNN (PyTorch->ONNX) + RandomForest (scikit-learn) + this HSV heuristic,
combined by a calibrated logistic meta-learner.
"""

from __future__ import annotations

from typing import Dict, List

import cv2
import numpy as np

from hsv_features import condition_cues

ALLOWED_FINDINGS = (
    "Surface Discoloration",
    "Surface Damage",
    "Possible Mold-Like Growth",
    "Shriveling",
    "Sprouting",
)

STATUS_VOCAB = {
    "clear": ("GREEN", "NO OBVIOUS VISIBLE DAMAGE"),
    "review": ("YELLOW", "NEEDS REVIEW"),
    "suspect": ("RED", "VISIBLE DAMAGE"),
}

# Thresholds tuned on synthetic copy-paste scope; field validation pending.
TH_SUSPECT_DARK = 0.115
TH_REVIEW_DARK = 0.045
TH_REVIEW_GREENTOP = 0.16
TH_REVIEW_SATSTD = 62.0


def heuristic_probs(cues: Dict[str, float]) -> np.ndarray:
    """Soft probability-ish scores over [clear, review, suspect].

    Deterministic mapping from cue space; used both standalone (Phase 1
    fallback) and as meta-learner input. NOT a calibrated probability.
    """
    dark = cues["darkRatio"]
    green = cues["greenTop"]
    sat_std = cues["satStd"]
    pale = cues["paleRatio"]

    suspect_sc = max(0.0, (dark - TH_REVIEW_DARK) / max(1e-6, TH_SUSPECT_DARK - TH_REVIEW_DARK)) ** 1.4
    suspect_sc = min(1.0, suspect_sc)
    review_sc = min(1.0, max(
        dark / TH_REVIEW_DARK * 0.55,
        green / TH_REVIEW_GREENTOP * 0.8,
        (sat_std - 45.0) / 60.0 * 0.4,
        pale * 1.2,
    ))
    review_sc = max(0.0, review_sc - 0.75 * suspect_sc)

    total = suspect_sc + review_sc + 0.35  # prior on clear
    probs = np.array([0.35 / total, review_sc / total, suspect_sc / total], dtype=np.float64)
    return probs / probs.sum()


def heuristic_class(cues: Dict[str, float]) -> str:
    p = heuristic_probs(cues)
    return ("clear", "review", "suspect")[int(np.argmax(p))]


def damage_regions(bgr: np.ndarray) -> List[Dict[str, float]]:
    """Locate candidate damage regions (normalized cx, cy, r inside the crop).

    These are pixel-measured dark/blemished connected components - used by the
    3D inspection view, which displays them as clearly-labelled
    AI-INFERRED REGIONS (never as ground truth).
    """
    img = bgr
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v = hsv[..., 2]
    s = hsv[..., 1]
    dark = ((v < 75) & (s > 30)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel)
    h_img, w_img = img.shape[:2]
    regions: List[Dict[str, float]] = []
    n, labels, stats, centroids = cv2.connectedComponentsWithStats(dark, 8)
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < max(24.0, 0.0015 * h_img * w_img):
            continue
        cx, cy = centroids[i]
        r = float(np.sqrt(area / np.pi)) * 1.35
        regions.append({
            "x": float(np.clip(cx / w_img, 0.0, 1.0)),
            "y": float(np.clip(cy / h_img, 0.0, 1.0)),
            "r": float(np.clip(r / (0.5 * (h_img + w_img)), 0.03, 0.45)),
        })
    regions.sort(key=lambda r: -(r["r"]))
    return regions[:5]


def derive_findings(cues: Dict[str, float], regions: List[Dict[str, float]]) -> List[Dict]:
    """Map measured cues to allowed findings with evidence strings.

    Confidence here is a visual-evidence strength (0..1), NEVER a food-safety
    probability.
    """
    out: List[Dict] = []
    dark = cues["darkRatio"]
    green = cues["greenTop"]
    pale = cues["paleRatio"]
    rough = cues["edgeDensity"]

    if dark >= TH_REVIEW_DARK:
        # Dark + mottled + rough patches read as possible mold-like growth;
        # smoother dark patches read as discoloration.
        mold_like = dark >= TH_SUSPECT_DARK and cues["laplacianVar"] > 120.0
        if mold_like:
            out.append({
                "kind": "Possible Mold-Like Growth",
                "confidence": float(min(0.93, 0.55 + dark)),
                "evidence": f"dark mottled patches cover {dark * 100:.1f}% of the visible surface "
                            f"with rough texture (measured via HSV dark-ratio {dark:.3f}, "
                            f"texture variance {cues['laplacianVar']:.0f})",
            })
        else:
            out.append({
                "kind": "Surface Discoloration",
                "confidence": float(min(0.9, 0.5 + dark * 2.2)),
                "evidence": f"darkened regions cover {dark * 100:.1f}% of the visible surface "
                            f"(measured dark-ratio {dark:.3f})",
            })
        if len(regions) >= 2 or dark >= TH_SUSPECT_DARK:
            out.append({
                "kind": "Surface Damage",
                "confidence": float(min(0.88, 0.45 + dark)),
                "evidence": f"{len(regions)} separate damaged-looking region(s) located on the visible surface",
            })
    if green >= TH_REVIEW_GREENTOP:
        out.append({
            "kind": "Sprouting",
            "confidence": float(min(0.92, 0.5 + green * 1.5)),
            "evidence": f"green shoot-like colouring on {green * 100:.1f}% of the top quarter "
                        f"(measured green-top ratio {green:.3f})",
        })
    if pale > 0.14 and dark < TH_REVIEW_DARK:
        out.append({
            "kind": "Surface Damage",
            "confidence": float(min(0.85, 0.4 + pale)),
            "evidence": f"pale low-saturation patches cover {pale * 100:.1f}% of the visible surface "
                        f"(dried-gash cue {pale:.3f})",
        })
    if rough > 0.16 and cues["satStd"] < 40.0 and not out:
        out.append({
            "kind": "Shriveling",
            "confidence": float(min(0.8, 0.4 + rough)),
            "evidence": f"high surface micro-texture ({rough * 100:.1f}% edge pixels) with low saturation "
                        f"spread ({cues['satStd']:.1f}) - dry-looking skin",
        })
    # Vocabulary guard - never emit anything outside the allowed set
    return [f for f in out if f["kind"] in ALLOWED_FINDINGS][:4]


def analyze_crop(bgr: np.ndarray) -> Dict:
    """Full Phase-1 heuristic analysis of one onion crop."""
    cues = condition_cues(bgr)
    probs = heuristic_probs(cues)
    cls = ("clear", "review", "suspect")[int(np.argmax(probs))]
    regions = damage_regions(bgr)
    findings = derive_findings(cues, regions)
    status_color, status_label = STATUS_VOCAB[cls]
    return {
        "conditionClass": cls,
        "statusColor": status_color,
        "statusLabel": status_label,
        "confidence": float(probs.max()),
        "probs": [float(p) for p in probs],
        "cues": cues,
        "regions": regions,
        "findings": findings,
    }


if __name__ == "__main__":
    import sys
    img = cv2.imread(sys.argv[1])
    print(analyze_crop(img))
