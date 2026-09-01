"""ENSEMBLE INTELLIGENCE — fuse the rule engine with the ML classifier.

Two INDEPENDENT evidence streams look at the same measurements:
  * rules   (defects.py)  — transparent thresholds, computed confidences
  * model   (classifier.py) — RandomForest class probabilities
Fusion = noisy-OR per defect family; when the two streams disagree the fused
confidence is REDUCED and the disagreement is surfaced — never hidden.

Also computes GRADE PROBABILITIES (the problem statement's
"Grade A probability: XX% / URS probability: XX%") by Monte-Carlo: perturb the
measured features within realistic measurement noise, recompute the score,
and read off the grade distribution. These are computed, explainable numbers —
not invented.
"""
from __future__ import annotations

import random
from dataclasses import replace

from app.services.defects import DefectFinding
from app.services.features import OnionFeatures
from app.services.grading import assign_grade
from app.services.scoring import compute_score

# dataset class → defect families it implies
CLASS_TO_DEFECTS = {
    "rotten": ["rot"],
    "sprouted": ["sprouting"],
    "damaged": ["physical_damage", "surface_spots"],
    "discolored": ["discolored"],
    "deformed": ["deformed"],
    "undersized": ["undersized"],
    "healthy": [],
}
DEFECT_TO_CLASS = {
    "rot": "rotten", "sprouting": "sprouted", "physical_damage": "damaged",
    "surface_spots": "damaged", "discolored": "discolored",
    "deformed": "deformed", "undersized": "undersized",
}

# realistic measurement noise used by the Monte-Carlo (relative or absolute)
_PERTURB = [
    ("dark_region_ratio", "rel", 0.25), ("largest_spot_ratio", "rel", 0.30),
    ("dark_spot_count", "int", 2), ("edge_density", "rel", 0.20),
    ("green_top_ratio", "rel", 0.25), ("hue_circular_std_deg", "abs", 3.0),
    ("circularity", "abs", 0.02), ("solidity", "abs", 0.01),
    ("sat_mean", "rel", 0.08), ("val_mean", "rel", 0.08),
]


def fuse_findings(findings: list[DefectFinding], ml: dict | None,
                  rule_gated: bool = False) -> dict:
    """Fuse rule findings with ML probabilities.

    Returns per-defect fused confidences + an overall ensemble verdict.
    Rule-only mode (ml=None) degrades gracefully to the rule confidences.

    rule_gated=True (pile-scan mode): a DEFECT class wins only if the rule
    engine also detected evidence for it (two-stream consensus), except
    'undersized' (ML size proxy, allowed alone at p≥0.7 because rules honestly
    cannot judge pixel size). Prevents single-stream hallucinations on
    out-of-distribution pile photos.
    """
    per_defect: dict[str, dict] = {}
    ml_probs = {p["label"]: p["probability"] for p in (ml or {}).get("predictions", [])}

    for x in findings:
        entry = {"rule_status": x.status, "rule_confidence": x.confidence,
                 "ml_probability": None, "fused_confidence": x.confidence,
                 "ml_supports": None}
        if x.status == "detected":
            cls = DEFECT_TO_CLASS.get(x.name)
            p_ml = ml_probs.get(cls, 0.0) if ml_probs else None   # absent class = 0 support
            if p_ml is not None:
                entry["ml_probability"] = p_ml
                # noisy-OR: two independent witnesses agreeing
                fused = 1.0 - (1.0 - (x.confidence or 0.5)) * (1.0 - p_ml)
                if p_ml < 0.25:                    # model disagrees → damp + flag
                    fused = min(fused, x.confidence or 0.5) * 0.8
                    entry["ml_supports"] = False
                else:
                    entry["ml_supports"] = True
                entry["fused_confidence"] = round(min(0.97, fused), 2)
        per_defect[x.name] = entry

    # overall class verdict: ML prior boosted when its defect family fired
    if ml:
        scores = {lbl: p for lbl, p in ml_probs.items()}
        for x in findings:
            if x.status == "detected" and x.name in DEFECT_TO_CLASS:
                cls = DEFECT_TO_CLASS[x.name]
                if cls in scores:
                    scores[cls] = min(0.97, scores[cls] * 1.35)
        best = max(scores, key=scores.get) if scores else "healthy"
        rule_best = next((DEFECT_TO_CLASS[x.name] for x in findings
                          if x.status == "detected"
                          and x.name in ("rot", "sprouting", "physical_damage",
                                         "deformed", "discolored")), "healthy")
        if rule_gated:
            corroborated = {DEFECT_TO_CLASS[x.name] for x in findings
                            if x.status == "detected" and x.name in DEFECT_TO_CLASS}
            candidates = corroborated | {"healthy"}
            gated_best = max(candidates, key=lambda c: scores.get(c, 0.0))
            if best == "undersized" and scores.get("undersized", 0.0) >= 0.7:
                gated_best = "undersized"      # ML size proxy, strong probability
            best = gated_best
        agreement = (best == rule_best)
        return {
            "predicted_class": best,
            "confidence": round(scores.get(best, 0.0), 2),
            "agreement": "rules_and_model_agree" if agreement else "rules_and_model_disagree",
            "streams": {"rules": "rule_based_v1",
                        "model": (ml or {}).get("type"),
                        "model_trained_on": (ml or {}).get("trained_on"),
                        "model_val_accuracy": (ml or {}).get("val_accuracy"),
                        "rule_gated": rule_gated},
            "per_defect": per_defect,
        }
    # rule-only fallback
    best, conf = "healthy", 0.0
    for x in findings:
        if x.status == "detected" and x.name in DEFECT_TO_CLASS:
            cls = DEFECT_TO_CLASS[x.name]
            if conf < (x.confidence or 0):
                best, conf = cls, x.confidence or 0
    return {"predicted_class": best, "confidence": round(conf, 2),
            "agreement": "rules_only", "streams": {"rules": "rule_based_v1"},
            "per_defect": per_defect}


def grade_probabilities(f: OnionFeatures, findings: list[DefectFinding],
                        rules: dict, trials: int = 180, seed: int = 7) -> dict | None:
    """P(Grade A/B/C/URS) via Monte-Carlo over measurement noise.

    The score is recomputed on perturbed copies of the measured features;
    the resulting grade distribution is the probability estimate. Deterministic
    (fixed seed) so the same image always yields the same answer.
    """
    rng = random.Random(seed)
    counts = {"A": 0, "B": 0, "C": 0, "URS": 0}
    for _ in range(trials):
        ff = f
        for attr, mode, mag in _PERTURB:
            base = float(getattr(f, attr, 0.0) or 0.0)
            if mode == "rel":
                new = max(0.0, base * (1.0 + rng.uniform(-mag, mag)))
            elif mode == "int":
                new = max(0.0, base + rng.uniform(-mag, mag))
            else:
                new = max(0.0, base + rng.uniform(-mag, mag))
            ff = replace(ff, **{attr: new if attr != "dark_spot_count" else int(round(new))})
        score = compute_score(ff, findings, rules)
        counts[assign_grade(score.score, True, rules)["grade"]] += 1
    total = sum(counts.values())
    return {
        "probabilities": {g: round(c / total, 3) for g, c in counts.items()},
        "method": (f"Monte-Carlo ({trials} trials) over realistic measurement "
                   "noise (±15–30% per feature); score recomputed per trial"),
    }
