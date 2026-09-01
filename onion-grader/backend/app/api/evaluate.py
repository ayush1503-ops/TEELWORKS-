"""Evaluation endpoints — ACTUAL vs PREDICTED with real, measured metrics.

POST /api/evaluate              one labelled upload → predicted, correct?
GET  /api/evaluate/metrics      metrics over stored test uploads
POST /api/evaluate/dataset-test ⭐ runs a HELD-OUT test split (never used in
                                training) through the FULL production pipeline
                                (segmentation → features → ensemble) and
                                computes accuracy live — the SIH demo number.

HONESTY RULE: every number here is computed from images actually run through
the system, and every response states exactly which set it was measured on.
No general accuracy is claimed anywhere.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.core.config import PROJECT_ROOT
from app.core.security import enforce_rate_limit
from app.services import database as db
from app.services.analyzer import run_pipeline
from app.services.classifier import load_classifier

router = APIRouter(tags=["evaluation"])

VALID_LABELS = {"healthy", "rotten", "damaged", "sprouted", "undersized",
                "discolored", "deformed"}


def _compute_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    """Accuracy + per-class P/R/F1 + confusion matrix (scikit-learn)."""
    from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
    n = len(y_true)
    labels = sorted(set(y_true) | set(y_pred))
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    m: dict = {"accuracy": round(correct / n, 4) if n else 0.0, "n": n}
    p, r, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0)
    m["per_class"] = [
        {"label": lbl, "precision": round(float(pp), 3), "recall": round(float(rr), 3),
         "f1": round(float(ff), 3), "support": int(ss)}
        for lbl, pp, rr, ff, ss in zip(labels, p, r, f1, sup)]
    avg_p, avg_r, avg_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0)
    m["weighted_precision"] = round(float(avg_p), 3)
    m["weighted_recall"] = round(float(avg_r), 3)
    m["weighted_f1"] = round(float(avg_f1), 3)
    m["confusion_matrix"] = {"labels": labels,
                             "matrix": confusion_matrix(y_true, y_pred,
                                                        labels=labels).tolist()}
    return m


@router.post("/evaluate", summary="Test one labelled onion image against the pipeline")
async def evaluate_one(request: Request, file: UploadFile = File(...),
                       actual: str = Form(...)) -> dict:
    enforce_rate_limit(request.client.host if request.client else "unknown")
    actual = actual.strip().lower()
    if actual not in VALID_LABELS:
        raise HTTPException(status_code=422,
                            detail=f"actual must be one of: {sorted(VALID_LABELS)}")
    result = await run_upload(file)
    pred = result.get("predicted_class") or {}
    predicted = pred.get("label", "healthy")
    correct = predicted == actual

    db.save_eval({
        "created_at": db.now_iso(), "actual": actual, "predicted": predicted,
        "confidence": pred.get("confidence", 0.0), "correct": int(correct),
        "score": (result.get("quality_score") or {}).get("score"),
        "grade": (result.get("grade") or {}).get("grade"),
        "filename": result.get("image", {}).get("filename"),
    })
    return {
        "filename": result["image"]["filename"], "actual": actual,
        "predicted": predicted, "confidence": pred.get("confidence", 0.0),
        "correct": correct,
        "quality_score": (result.get("quality_score") or {}).get("score"),
        "grade": (result.get("grade") or {}).get("grade"),
        "analysis_id": result["analysis_id"],
        "top_defects": [d["label"] for d in result.get("defects", [])
                        if d.get("status") == "detected"],
    }


async def run_upload(file: UploadFile) -> dict:
    from app.services.analyzer import analyze_image
    return await analyze_image(file)


@router.get("/evaluate/metrics", summary="Metrics over stored test uploads")
def metrics() -> dict:
    rows = db.all_eval_results()
    if not rows:
        return {"n": 0, "metrics": None,
                "note": ("No test images evaluated yet. Metrics appear only after "
                         "labelled test images are run — no accuracy is claimed "
                         "before it is actually measured.")}
    y_true = [r["actual"] for r in rows]
    y_pred = [r["predicted"] for r in rows]
    m = _compute_metrics(y_true, y_pred)
    m["note"] = (f"Measured on {len(rows)} labelled test image(s) run on this system. "
                 "NOT a claim of general accuracy on unseen data.")
    return {"n": len(rows), "metrics": m, "results": rows}


@router.post("/evaluate/dataset-test",
             summary="⭐ DEMO: run a held-out test split through the full pipeline, live")
def dataset_test(dataset: str = "synthetic_v1", limit_per_class: int = 15) -> dict:
    limit = max(1, min(limit_per_class, 50))
    root = PROJECT_ROOT / "datasets" / dataset / "classes" / "test"
    if not root.exists():
        available = [p.name for p in (PROJECT_ROOT / "datasets").glob("*/classes/test")]
        raise HTTPException(
            status_code=404,
            detail=(f"Test split for '{dataset}' not found on this server. "
                    f"Available: {available or 'none'}. Generate one with "
                    "scripts/generate_synthetic_dataset.py or copy your field "
                    "dataset's test split here."))

    y_true, y_pred, files, skipped = [], [], [], 0
    for cls_dir in sorted(root.iterdir()):
        if not cls_dir.is_dir():
            continue
        for p in sorted(cls_dir.glob("*.jpg"))[:limit]:
            try:
                result = run_pipeline(p.read_bytes(), p.name, save=False)
            except Exception:
                skipped += 1
                continue
            label = cls_dir.name
            pred = result["predicted_class"]["label"]
            if result["status"] == "no_onion_detected":
                pred = "not_detected"
                skipped += 1
            y_true.append(label)
            y_pred.append(pred)
            files.append({"file": p.name, "actual": label, "predicted": pred,
                          "correct": label == pred,
                          "confidence": result["predicted_class"]["confidence"]})

    if not y_true:
        raise HTTPException(status_code=500, detail="No test images could be processed.")

    m = _compute_metrics(y_true, y_pred)
    _model, ml_meta = load_classifier()
    correct = sum(1 for f_ in files if f_["correct"])
    return {
        "dataset": dataset,
        "measured_live": True,
        "n_images": len(y_true),
        "n_correct": correct,
        "skipped": skipped,
        "metrics": m,
        "pipeline": ("identical production path: OpenCV segmentation → 20 measured "
                     "features → rule engine + RandomForest ensemble"),
        "model_trained_on": (ml_meta or {}).get("trained_on"),
        "model_val_accuracy": (ml_meta or {}).get("val_accuracy"),
        "note": (
            f"Accuracy {m['accuracy']*100:.1f}% was MEASURED just now on {len(y_true)} "
            f"held-out '{dataset}' test images the model never trained on. This "
            "describes performance on THIS test distribution (synthetic images) — "
            "it is not a claim about arbitrary field photos; field validation is "
            "pending."
        ),
        "files": files,
    }
