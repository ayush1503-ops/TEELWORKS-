"""ML CLASSIFIER (real model, honestly labelled).

Loads models/classifier.pkl when present. The payload records WHAT the model
was trained on (`trained_on`, e.g. "synthetic-v1") and its measured validation
accuracy within that distribution — surfaced to the UI so nobody mistakes a
synthetic bootstrap for field validation.

`ml_opinion` also returns EXPLAINABILITY DRIVERS: the features whose values
deviate most (z-score) from the healthy-class training distribution — i.e.
WHY this onion is classified away from healthy.
"""
from __future__ import annotations

import pickle

from app.core.config import PROJECT_ROOT
from app.services.features import OnionFeatures

MODEL_PATH = PROJECT_ROOT / "models" / "classifier.pkl"

_cache: dict = {"loaded": False, "model": None, "meta": None}


def load_classifier():
    """Return (model, meta_dict) or (None, None). Cached after first load."""
    if _cache["loaded"]:
        return _cache["model"], _cache["meta"]
    _cache["loaded"] = True
    if not MODEL_PATH.exists():
        return None, None
    try:
        with open(MODEL_PATH, "rb") as fh:
            payload = pickle.load(fh)
        _cache["model"] = payload.get("model")
        _cache["meta"] = {
            "trained_on": payload.get("trained_on", "unknown"),
            "val_accuracy": payload.get("val_accuracy"),
            "n_train": payload.get("n_train"),
            "feature_keys": payload.get("feature_keys", []),
            "algorithm": payload.get("algorithm", "RandomForest"),
            "class_stats": payload.get("class_stats", {}),
        }
        return _cache["model"], _cache["meta"]
    except Exception:
        return None, None


def _drivers(f: OnionFeatures, meta: dict) -> list[dict] | None:
    """Top features pulling this sample AWAY from the healthy class."""
    stats = meta.get("class_stats") or {}
    healthy = stats.get("healthy")
    keys = meta.get("feature_keys") or []
    if not healthy or not keys:
        return None
    vec = f.vector()
    scored = []
    for i, key in enumerate(keys):
        mu, sd = healthy.get(key, (0.0, 1.0))
        x = float(vec[i])
        z = (x - float(mu)) / float(sd) if float(sd) > 0 else 0.0
        scored.append((abs(z), key, x, float(mu), z))
    scored.sort(reverse=True)
    return [{"feature": k, "value": round(x, 3), "healthy_mean": round(mu, 3),
             "z": round(z, 1)} for _a, k, x, mu, z in scored[:3]]


def ml_opinion(f: OnionFeatures) -> dict | None:
    """Class probabilities from the trained model (+ explanation drivers)."""
    model, meta = load_classifier()
    if model is None:
        return None
    try:
        probs = model.predict_proba([f.vector()])[0]
        ranked = sorted(zip(model.classes_, probs), key=lambda t: -t[1])
        out = {
            "type": "random_forest_baseline",
            "trained_on": meta["trained_on"],
            "val_accuracy": meta["val_accuracy"],
            "predictions": [{"label": str(lbl), "probability": round(float(p), 3)}
                            for lbl, p in ranked[:4]],
        }
        drivers = _drivers(f, meta)
        if drivers:
            out["drivers_vs_healthy"] = drivers
        return out
    except Exception:
        return None
