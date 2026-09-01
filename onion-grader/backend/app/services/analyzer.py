"""ORCHESTRATOR — one onion image through every layer, honestly.

    validate (security)  →  Layer A: OpenCV detect + measure
                        →  Layer B: defect findings + ML (ensemble fusion)
                        →  Layer C: transparent quality score
                        →  Layer D: configurable grade (+ Monte-Carlo grade probs)
                        →  annotated image + DB row + JSON response

`analyze_image`  — used by /api/analyze, /api/batch, /api/evaluate (uploads)
`run_pipeline`   — the identical analysis for server-side images (held-out
                   test-set demo), optionally without saving to the DB.
Both go through THE SAME code path — the demo number is the production number.
"""
from __future__ import annotations

import json

from fastapi import UploadFile

from app.core.config import APP_VERSION, CURRENT_PHASE
from app.core.security import validate_upload
from app.services import database as db
from app.services import preprocessing as pre
from app.services.classifier import load_classifier, ml_opinion
from app.services.defects import detect_defects, findings_to_dicts
from app.services.ensemble import fuse_findings, grade_probabilities
from app.services.features import OnionFeatures, extract_features, sprout_band_bbox
from app.services.grading import assign_grade, load_rules
from app.services.scoring import analysis_confidence, compute_score

_DISCLAIMERS_BASE = [
    "Internal quality cannot be reliably determined from this image alone.",
    "Grades use PROTOTYPE configurable rules, not an official standard.",
    "Size is measured in pixels until a physical reference is calibrated.",
]


def _disclaimers(ml_meta: dict | None) -> list[str]:
    out = list(_DISCLAIMERS_BASE)
    if ml_meta:
        out.append(
            f"ML component is a RandomForest trained on {ml_meta.get('trained_on', '?')} "
            f"images (validation accuracy {ml_meta.get('val_accuracy')} measured on that "
            "same distribution) — FIELD VALIDATION IS PENDING; treat predictions as "
            "prototype assistance, not ground truth."
        )
    else:
        out.append("Defect confidences are computed from measured feature magnitudes "
                   "(rule engine v1); no trained ML model is loaded.")
    return out


async def analyze_image(file: UploadFile) -> dict:
    """Upload entry point: validate → run the identical production pipeline."""
    info = await validate_upload(file)          # raises 4xx on bad input
    data = info.pop("data")
    return run_pipeline(data, info["filename"], save=True)


def run_pipeline(data: bytes, filename: str, save: bool = True) -> dict:
    """The FULL analysis pipeline on raw image bytes (production code path)."""
    rules = load_rules()

    img = pre.load_bgr(data)
    if img is None:
        raise ValueError("image could not be decoded")
    h, w = img.shape[:2]
    image_meta = {
        "filename": filename,
        "format": ("PNG" if filename.lower().endswith(".png") else "JPEG"),
        "width": w, "height": h,
        "size_bytes": len(data),
        "megapixels": round(w * h / 1e6, 2),
        "aspect_ratio": round(w / h, 3),
    }

    # ---------- Layer A: OpenCV ----------
    det = pre.segment_onion(img, rules)

    if not det.found:
        annotated_b64 = pre.to_jpeg_b64(det.image, 80, 640) if det.image is not None else None
        row = _db_row(image_meta, det, None, None, None, None, None, None, "no_onion")
        row["annotated_b64"] = annotated_b64
        if save:
            db.save_analysis(row)
        return {
            "analysis_id": row["id"],
            "created_at": row["created_at"],
            "status": "no_onion_detected",
            "analysis_available": True,
            "image": image_meta,
            "detection": {"found": False, "reason": det.reason, "method": None,
                          "bbox": None, "area_fraction": 0.0, "solidity": 0.0,
                          "annotated_image_b64": annotated_b64},
            "features": OnionFeatures().dict(),
            "defects": [],
            "quality_score": None,
            "grade": assign_grade(None, False, rules),
            "grade_probabilities": None,
            "predicted_class": {"label": "no_onion", "confidence": 0.0},
            "analysis_confidence": {"value": 0.0, "basis": "onion not detected"},
            "model": {"type": "rule_based_v1", "trained_ml_loaded": False},
            "capture_warnings": {},
            "disclaimers": _disclaimers(load_classifier()[1]),
            "phase": CURRENT_PHASE,
            "app_version": APP_VERSION,
        }

    feats = extract_features(det, rules)

    # ---------- Layer B: rules + ML → ensemble ----------
    findings = detect_defects(feats, rules)
    ml = ml_opinion(feats)
    _model, ml_meta = load_classifier()
    ens = fuse_findings(findings, ml)
    defect_dicts = findings_to_dicts(findings)
    for d in defect_dicts:
        fused = ens["per_defect"].get(d["name"], {})
        d["fused_confidence"] = fused.get("fused_confidence", d.get("confidence"))
        d["ml_supports"] = fused.get("ml_supports")

    gprob = grade_probabilities(feats, findings, rules)

    # ---------- Layer C + D ----------
    score = compute_score(feats, findings, rules)
    grade = assign_grade(score.score, True, rules)
    conf, conf_basis = analysis_confidence(feats, True)

    # ---------- explainability ----------
    annotated = pre.draw_annotations(det, spots=feats.spot_boxes,
                                      sprout_band=sprout_band_bbox(det))
    annotated_b64 = pre.to_jpeg_b64(annotated)
    thumb_b64 = pre.to_jpeg_b64(det.image, 70, 320)

    row = _db_row(image_meta, det, feats, findings, score, grade, conf, None,
                  ens["predicted_class"])
    row["thumb_b64"] = thumb_b64
    row["annotated_b64"] = annotated_b64
    if save:
        db.save_analysis(row)

    return {
        "analysis_id": row["id"],
        "created_at": row["created_at"],
        "status": "analysed",
        "analysis_available": True,
        "image": image_meta,
        "detection": {"found": True, "reason": "", "method": det.method,
                      "bbox": list(det.bbox) if det.bbox else None,
                      "area_fraction": det.area_fraction, "solidity": det.solidity,
                      "annotated_image_b64": annotated_b64},
        "features": feats.dict(),
        "defects": defect_dicts,
        "quality_score": {"score": score.score, "breakdown": score.breakdown,
                          "penalties": score.penalties, "reasons": score.reasons},
        "grade": grade,
        "grade_probabilities": gprob,
        "predicted_class": {"label": ens["predicted_class"],
                            "confidence": ens["confidence"]},
        "analysis_confidence": {"value": conf, "basis": conf_basis},
        "model": {
            "type": "rules+rf_ensemble" if ml else "rule_based_v1",
            "trained_ml_loaded": ml is not None,
            "trained_on": (ml_meta or {}).get("trained_on"),
            "validation_accuracy_on_training_dist": (ml_meta or {}).get("val_accuracy"),
            "ml_predictions": ml,
            "ensemble_agreement": ens["agreement"],
        },
        "capture_warnings": {"lighting_poor": feats.lighting_poor,
                             "shadow_risk": feats.shadow_risk},
        "disclaimers": _disclaimers(ml_meta),
        "phase": CURRENT_PHASE,
        "app_version": APP_VERSION,
    }


def _db_row(info, det, feats, findings, score, grade, conf, diameter_mm, pred_label) -> dict:
    return {
        "id": db.new_id("ON"),
        "created_at": db.now_iso(),
        "filename": info.get("filename"),
        "format": info.get("format"),
        "img_w": info.get("width"),
        "img_h": info.get("height"),
        "onion_found": 1 if det.found else 0,
        "quality_score": score.score if score else None,
        "grade": grade.get("grade") if grade else None,
        "rule_version": (grade or {}).get("rule_version"),
        "defects_json": json.dumps(findings_to_dicts(findings)) if findings else "[]",
        "reasons_json": json.dumps(score.reasons) if score else "[]",
        "breakdown_json": json.dumps({"components": score.breakdown,
                                      "penalties": score.penalties}) if score else "{}",
        "analysis_confidence": conf,
        "diameter_px": feats.equivalent_diameter_px if feats else None,
        "circularity": feats.circularity if feats else None,
        "recommendation": (grade or {}).get("recommendation"),
        "onion_count": 1,
        "thumb_b64": None,
        "annotated_b64": None,
    }
