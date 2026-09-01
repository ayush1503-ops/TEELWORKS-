"""LAYER C — transparent quality scoring.

quality_score = Σ(component points) − Σ(defect penalties × severity multiplier)

Every component is a 0–1 subscore computed from ONE measured feature with a
stated mapping, then multiplied by its configurable max points. The full
breakdown is returned so the UI/report can show exactly WHY the score is 87.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.defects import DefectFinding
from app.services.features import OnionFeatures


@dataclass
class ScoreResult:
    score: int                      # 0..100
    breakdown: dict                 # component → points awarded (max shown too)
    penalties: dict                 # defect → points subtracted
    reasons: list                   # [{level: good|warn|bad, text}]
    subscores: dict                 # raw 0..1 values for transparency


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _lerp_down(value: float, best: float, worst: float, floor: float = 0.2) -> float:
    """HIGHER-is-better metric (circularity…): value ≥ best → 1.0, ≤ worst → floor."""
    if value >= best:
        return 1.0
    if value <= worst:
        return floor
    return floor + (1.0 - floor) * (value - worst) / (best - worst)


def _lerp_low_good(value: float, best: float, worst: float, floor: float = 0.2) -> float:
    """LOWER-is-better metric (hue spread, edge density): value ≤ best → 1.0."""
    if value <= best:
        return 1.0
    if value >= worst:
        return floor
    return floor + (1.0 - floor) * (worst - value) / (worst - best)


def compute_score(f: OnionFeatures, findings: list[DefectFinding], rules: dict) -> ScoreResult:
    cfg = rules.get("scoring", {})
    comp_max: dict[str, int] = cfg.get("components", {})
    pen_max: dict[str, int] = cfg.get("defect_penalties", {})
    sev_mult: dict[str, float] = cfg.get("severity_multipliers", {"minor": 0.4, "moderate": 0.7, "severe": 1.0})

    # ---------- raw 0..1 subscores (each tied to ONE measurement) ----------
    appearance = _clamp01(1.0 - f.dark_region_ratio * 4.0)
    size = 1.0 - 0.5 * _clamp01((0.08 - f.area_fraction) / 0.08) if f.area_fraction < 0.08 else 1.0
    shape = 0.6 * _lerp_down(f.circularity, best=0.95, worst=0.60) + \
            0.4 * _lerp_down(f.solidity, best=0.95, worst=0.80)
    colour = _lerp_low_good(f.hue_circular_std_deg, best=6.0, worst=32.0)
    skin = _lerp_low_good(f.edge_density, best=0.03, worst=0.18)
    clean = _clamp01(1.0 - min(1.0, f.dark_spot_count * 0.06 + f.largest_spot_ratio * 8.0))

    subs = {"appearance": appearance, "size": size, "shape": shape,
            "colour_uniformity": colour, "skin_condition": skin,
            "surface_cleanliness": clean}

    breakdown, reasons = {}, []
    labels = {
        "appearance": "external appearance (dark-area free)",
        "size": "size in frame (proxy until mm calibration)",
        "shape": "shape regularity",
        "colour_uniformity": "colour uniformity",
        "skin_condition": "skin condition (few breaks/edges)",
        "surface_cleanliness": "surface cleanliness (spot-free)",
    }
    for key, maxp in comp_max.items():
        pts = round(subs.get(key, 0.0) * float(maxp), 1)
        breakdown[key] = {"points": pts, "max": float(maxp), "subscore": round(subs.get(key, 0.0), 3)}
        level = "good" if subs.get(key, 0) >= 0.75 else ("warn" if subs.get(key, 0) >= 0.45 else "bad")
        icon = {"good": "✓", "warn": "⚠", "bad": "✗"}[level]
        reasons.append({"level": level,
                        "text": f"{icon} {labels.get(key, key)}: {pts:.0f}/{maxp} points"})

    base = sum(v["points"] for v in breakdown.values())

    # ---------- defect penalties (only DETECTED findings count) ----------
    penalties = {}
    for x in findings:
        if x.status == "detected" and x.name in pen_max:
            p = round(float(pen_max[x.name]) * sev_mult.get(x.severity or "minor", 0.7), 1)
            penalties[x.name] = {"points": p, "max": float(pen_max[x.name]), "severity": x.severity}
            reasons.append({"level": "bad", "text": f"✗ {x.label}: −{p:.0f} points ({x.severity})"})

    total = int(round(max(0.0, min(100.0, base - sum(p["points"] for p in penalties.values())))))

    # capture-quality warnings (honest context, not score changes)
    if f.lighting_poor:
        reasons.append({"level": "warn",
                        "text": "⚠ Poor lighting detected — measurements less reliable"})
    if f.shadow_risk:
        reasons.append({"level": "warn",
                        "text": "⚠ Strong shadows in background — retake under even light for best results"})

    return ScoreResult(score=total, breakdown=breakdown, penalties=penalties,
                       reasons=reasons, subscores={k: round(v, 3) for k, v in subs.items()})


def analysis_confidence(f: OnionFeatures, det_found: bool) -> tuple[float, str]:
    """How much the IMAGE itself supports this analysis (not model confidence).
    Built from lighting, framing, shape solidity — fully disclosed."""
    if not det_found:
        return 0.0, "onion not detected — no analysis made"
    q = 0.0
    notes = []
    if not f.lighting_poor:
        q += 0.35; notes.append("adequate lighting (+0.35)")
    else:
        notes.append("poor lighting (+0)")
    if 0.04 <= f.area_fraction <= 0.60:
        q += 0.30; notes.append("good framing (+0.30)")
    elif f.area_fraction > 0.60:
        q += 0.15; notes.append("onion very close/edge-cut (+0.15)")
    else:
        notes.append("onion small in frame (+0)")
    if f.solidity >= 0.85:
        q += 0.20; notes.append("clean segmentation (+0.20)")
    else:
        notes.append("irregular segmentation (+0)")
    if not f.shadow_risk:
        q += 0.15; notes.append("no strong shadows (+0.15)")
    else:
        notes.append("shadows present (+0)")
    conf = round(min(0.95, 0.45 + 0.5 * q), 2)
    return conf, "image-evidence quality: " + "; ".join(notes)
