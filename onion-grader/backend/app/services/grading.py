"""LAYER D — grading: quality score (+ size when calibrated) → grade.

Rules live in config/grading_rules.yaml. This module only READS them, stamps
every answer with the rule_version, and attaches the disclaimer — so a grade is
always traceable to the exact rule set that produced it.
"""
from __future__ import annotations

import os
import time

import yaml

from app.core.config import GRADING_RULES_PATH

_cache: dict = {"mtime": None, "rules": None, "loaded": 0.0}

DEFAULT_RULES: dict = {
    "rule_version": "builtin-fallback",
    "official_standard": False,
    "disclaimer": "Built-in fallback rules (grading_rules.yaml missing).",
    "grade_thresholds": {"A": {"min_score": 80}, "B": {"min_score": 65},
                         "C": {"min_score": 45}, "URS": {"min_score": 0}},
    "recommendations": {"A": "Accept — best quality", "B": "Accept",
                        "C": "Accept with price differential", "URS": "Reject / URS"},
    "scoring": {"components": {"appearance": 25, "size": 10, "shape": 15,
                               "colour_uniformity": 15, "skin_condition": 15,
                               "surface_cleanliness": 10},
                "defect_penalties": {"rot": 45, "sprouting": 30, "physical_damage": 25,
                                     "surface_spots": 15, "deformed": 15, "discolored": 10},
                "severity_multipliers": {"minor": 0.4, "moderate": 0.7, "severe": 1.0}},
    "defect_rules": {},
    "analysis": {},
    "defect_to_class": {},
}


def load_rules(force: bool = False) -> dict:
    """Load grading rules YAML, cached by file mtime (edit → next request uses it)."""
    global _cache
    now = time.time()
    if (not force and _cache["rules"] is not None
            and now - _cache["loaded"] < 5
            and _cache["mtime"] == _rules_mtime()):
        return _cache["rules"]
    try:
        with open(GRADING_RULES_PATH, "r", encoding="utf-8") as fh:
            rules = yaml.safe_load(fh) or {}
        # merge over defaults so missing keys never crash the pipeline
        merged = {**DEFAULT_RULES, **rules}
        merged["scoring"] = {**DEFAULT_RULES["scoring"], **(rules.get("scoring") or {})}
        merged["analysis"] = {**DEFAULT_RULES["analysis"], **(rules.get("analysis") or {})}
        _cache = {"mtime": _rules_mtime(), "rules": merged, "loaded": now}
        return merged
    except FileNotFoundError:
        return DEFAULT_RULES


def _rules_mtime():
    try:
        return os.path.getmtime(GRADING_RULES_PATH)
    except OSError:
        return None


def assign_grade(score: int | None, found: bool, rules: dict,
                 diameter_mm: float | None = None) -> dict:
    """score → grade letter via configured thresholds; Undetermined when no onion."""
    if not found or score is None:
        return {"grade": "UNDETERMINED", "label": "Not determined",
                "recommendation": ("No onion detected — retake on a plain, "
                                   "contrasting background with even light"),
                "rule_version": rules.get("rule_version", "?"),
                "official": bool(rules.get("official_standard", False)),
                "basis": "onion not detected; no grade assigned",
                "disclaimer": rules.get("disclaimer", "")}

    thresholds = rules.get("grade_thresholds", DEFAULT_RULES["grade_thresholds"])
    grade = "URS"
    for letter in ("A", "B", "C"):
        if score >= float(thresholds.get(letter, {}).get("min_score", 10**9)):
            grade = letter
            break

    basis = (f"quality score {score}/100 ≥ "
             f"{thresholds.get(grade, {}).get('min_score')} ({grade} threshold)")

    # Optional mm-based size rule — only when calibration exists (Phase 8)
    size_note = None
    size_cfg = rules.get("size_rules", {})
    if size_cfg.get("calibrated") and diameter_mm is not None:
        bands = size_cfg.get("diameter_mm", {})
        for letter in ("A", "B", "C"):
            lo, hi = bands.get(letter, [None, None])
            if (lo is None or diameter_mm >= lo) and (hi is None or diameter_mm < hi):
                if grade == "A" and letter != "A":
                    grade = letter
                    basis += f"; downgraded by size rule (Ø{diameter_mm:.0f}mm → {letter})"
                break
        size_note = f"diameter {diameter_mm:.0f} mm applied from size_rules"
    else:
        size_note = "size in mm NOT applied (no calibration)"

    return {
        "grade": grade,
        "label": {"A": "Grade A", "B": "Grade B", "C": "Grade C",
                  "URS": "URS / Reject"}[grade],
        "recommendation": rules.get("recommendations", {}).get(grade, ""),
        "rule_version": rules.get("rule_version", "?"),
        "official": bool(rules.get("official_standard", False)),
        "basis": basis,
        "size_rule": size_note,
        "disclaimer": rules.get("disclaimer", ""),
    }
