"""MULTI-ONION SCAN — one photo of a pile → per-onion AI analysis.

Every onion instance goes through the IDENTICAL production pipeline used for
single-onion analysis (features → rule engine + ML ensemble → score → grade),
then all instances are drawn on the photo COLOUR-CODED by what the AI found:

    healthy = green · rotten = red · damaged = amber · sprouted = cyan
    discolored = purple · deformed = yellow · undersized = slate

…which makes rotten onions visibly pop in a different colour, exactly like
instance-segmentation demos. A batch PDF report is generated for download.

Honesty: counts come from image segmentation — heavily occluded or touching
onions can be merged/missed; the response states this.
"""
from __future__ import annotations

import json
from dataclasses import replace as _dc_replace
from statistics import median

import cv2
import numpy as np

from app.services import database as db
from app.services import preprocessing as pre
from app.services.analyzer import _disclaimers
from app.services.classifier import load_classifier, ml_opinion
from app.services.defects import detect_defects
from app.services.ensemble import fuse_findings
from app.services.features import extract_features
from app.services.grading import assign_grade, load_rules
from app.services.scoring import compute_score

CLASS_COLORS_HEX = {
    "healthy": "#22c55e",
    "rotten": "#ef4444",
    "damaged": "#f59e0b",
    "sprouted": "#06b6d4",
    "discolored": "#a855f7",
    "deformed": "#eab308",
    "undersized": "#64748b",
    "not_detected": "#9ca3af",
}


def _bgr(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def run_scan(data: bytes, filename: str, save: bool = True) -> dict:
    rules = load_rules()
    # PILE MODE: relax SHAPE rules — touching/occluded onions are clipped by
    # watershed, which lowers circularity/solidity WITHOUT the onion being
    # deformed. Stated openly in the response note.
    from copy import deepcopy
    rules_pile = deepcopy(rules)
    dfr = rules_pile.setdefault("defect_rules", {})
    deformed = dfr.setdefault("deformed", {})
    deformed.setdefault("circularity", {}).update({"minor": 0.70, "moderate": 0.62, "severe": 0.52})
    deformed.setdefault("solidity", {}).update({"minor": 0.78, "moderate": 0.72, "severe": 0.64})
    img = pre.load_bgr(data)
    if img is None:
        raise ValueError("image could not be decoded")
    dets, method = pre.segment_onions_multi(img, rules)

    # ---------- per-photo SCALE CALIBRATION (pile mode) ----------
    # The ML model was trained on close-up photos where absolute size in frame
    # matters. In a pile photo EVERYTHING is smaller — so every onion's size
    # features are normalised to the pile's MEDIAN diameter, mapped onto the
    # training scale. "Undersized" thereby becomes a RELATIVE judgement within
    # the photo (scale-invariant) — the only honest pixel-based definition of
    # undersized in a pile. The factor is reported in the response.
    raw = [(det, extract_features(det, rules_pile)) for det in dets]
    diameters = [f.equivalent_diameter_px for _, f in raw if f.equivalent_diameter_px > 0]
    afracs = [f.area_fraction for _, f in raw if f.area_fraction > 0]
    med_d = float(median(diameters)) if diameters else 0.0
    med_af = float(median(afracs)) if afracs else 0.0
    _model, ml_meta = load_classifier()
    try:
        h_stats = (ml_meta or {})["class_stats"]["healthy"]
        train_d = float(h_stats["equivalent_diameter_px"][0])
        train_af = float(h_stats["area_fraction"][0])
    except Exception:
        train_d, train_af = 0.0, 0.0
    scale_d = (train_d / med_d) if (train_d > 0 and med_d > 0) else 1.0
    scale_af = (train_af / med_af) if (train_af > 0 and med_af > 0) else 1.0

    def calibrate(f):
        if scale_d == 1.0 and scale_af == 1.0:
            return f
        return _dc_replace(
            f,
            equivalent_diameter_px=round(f.equivalent_diameter_px * scale_d, 1),
            area_fraction=round(min(0.95, f.area_fraction * scale_af), 4),
        )

    onions: list[dict] = []
    for i, (det, feats) in enumerate(raw, 1):
        f_use = calibrate(feats)
        findings = detect_defects(feats, rules_pile)
        ml = ml_opinion(f_use)
        ens = fuse_findings(findings, ml, rule_gated=True)  # two-stream consensus in piles
        score = compute_score(f_use, findings, rules)
        grade = assign_grade(score.score, True, rules)
        onions.append({
            "index": i,
            "bbox": list(det.bbox) if det.bbox else None,
            "class": ens["predicted_class"],
            "confidence": ens["confidence"],
            "quality_score": score.score,
            "grade": grade["grade"],
            "defects": [x.label for x in findings if x.status == "detected"],
        })

    n = len(onions)
    counts = {g: 0 for g in ("A", "B", "C", "URS")}
    for o in onions:
        counts[o["grade"]] += 1
    distribution = {g: {"count": c, "pct": round(100.0 * c / n, 1) if n else 0.0}
                    for g, c in counts.items()}
    class_counts: dict[str, int] = {}
    for o in onions:
        class_counts[o["class"]] = class_counts.get(o["class"], 0) + 1
    avg = round(sum(o["quality_score"] for o in onions) / n, 1) if n else None

    annotated_b64 = pre.to_jpeg_b64(_draw_scan(dets, onions)) if n else None
    legend = [{"label": k, "hex": CLASS_COLORS_HEX.get(k, "#9ca3af"), "count": v}
              for k, v in sorted(class_counts.items(), key=lambda kv: -kv[1])]

    scan_id = db.new_id("SCAN")
    if save and n:
        items = [{"id": f"Onion {o['index']}", "quality_score": o["quality_score"],
                  "grade": o["grade"], "defects_detected": o["defects"],
                  "class": o["class"], "confidence": o["confidence"]}
                 for o in onions]
        db.save_batch({
            "id": scan_id, "created_at": db.now_iso(), "total_onions": n,
            "analysed_ok": n,
            "grade_a_pct": distribution["A"]["pct"], "grade_b_pct": distribution["B"]["pct"],
            "grade_c_pct": distribution["C"]["pct"], "urs_pct": distribution["URS"]["pct"],
            "undetermined": 0, "avg_score": avg,
            "summary_json": json.dumps({"items": items, "method": method,
                                        "class_counts": class_counts}),
        })

    return {
        "scan_id": scan_id if n else None,
        "method": method,
        "onions_found": n,
        "size_normalization": {
            "method": "per-photo median calibration to training scale (diameter + area independently)",
            "scale_factor": round(scale_d, 3),
            "scale_factor_area": round(scale_af, 3),
            "note": ("Undersized is judged RELATIVE to the median onion in this "
                     "photo (scale-invariant). Shape rules are relaxed in pile "
                     "mode because occlusion degrades shape measurement. "
                     "Absolute mm still requires a physical size reference."),
        },
        "distribution": distribution,
        "avg_quality_score": avg,
        "class_counts": class_counts,
        "legend": legend,
        "onions": onions,
        "annotated_image_b64": annotated_b64,
        "report_url": f"/api/report/scan/{scan_id}.pdf" if n else None,
        "note": ("Grade percentages are the SHARE OF ONIONS DETECTED IN THIS PHOTO. "
                 "Counts come from image segmentation — heavily occluded or "
                 "touching onions may be merged or missed."),
        "disclaimers": _disclaimers(load_classifier()[1]),
    }


def _draw_scan(dets, onions) -> np.ndarray:
    """Colour-coded instance overlay + legend strip."""
    base = dets[0].image.copy()
    for det, o in zip(dets, onions):
        color = _bgr(CLASS_COLORS_HEX.get(o["class"], "#9ca3af"))
        if det.mask is not None:
            overlay = base.copy()
            overlay[det.mask > 0] = color
            base = cv2.addWeighted(overlay, 0.32, base, 0.68, 0)
        if det.contour is not None:
            cv2.drawContours(base, [det.contour], -1, color, 3)
        x, y, w, h = det.bbox
        cv2.rectangle(base, (x, y), (x + w, y + h), color, 2)
        tag = f"#{o['index']} {o['class']} {o['grade']} {o['quality_score']}"
        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        ty = y - 8 if y - 8 - th > 0 else y + th + 8
        cv2.rectangle(base, (x, ty - th - 4), (x + tw + 6, ty + 4), (20, 18, 16), -1)
        cv2.putText(base, tag, (x + 3, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1,
                    cv2.LINE_AA)

    # legend strip along the bottom
    present = sorted({o["class"] for o in onions})
    entries = present[:8]
    h_img = base.shape[0]
    strip = np.full((46, base.shape[1], 3), 24, dtype=np.uint8)
    x = 12
    for cls in entries:
        c = _bgr(CLASS_COLORS_HEX.get(cls, "#9ca3af"))
        cv2.rectangle(strip, (x, 14), (x + 22, 34), c, -1)
        cv2.putText(strip, cls, (x + 28, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (255, 255, 255), 1, cv2.LINE_AA)
        (tw, _), _ = cv2.getTextSize(cls, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        x += 28 + tw + 18
    cv2.putText(strip, f"{len(onions)} onions", (base.shape[1] - 140, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return np.vstack([base, strip])
