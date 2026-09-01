"""LAYER B (v1: rule engine) — defect findings from MEASURED features.

Honesty contract (SIH requirement #20):
  * every confidence below is COMPUTED from how far a measurement exceeds its
    configured threshold — no invented numbers, no random values;
  * if the image cannot support a claim, the finding returns
    status="insufficient_evidence" with the reason — e.g. internal rot
    (invisible in a photo) and size in mm (no calibration);
  * `basis` always states HOW the conclusion was reached.

When a trained ML model exists (Phase 5), `classifier.py` can ADD probability
estimates to these findings — the rules stay as the explainable fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from app.services.features import OnionFeatures

CONF_CAP = 0.95
CONF_FLOOR = 0.50


@dataclass
class DefectFinding:
    name: str                      # machine name (matches YAML keys)
    label: str                     # human label
    status: str                    # detected | not_detected | insufficient_evidence
    confidence: float | None       # 0..1 — only when detected
    severity: str | None           # minor | moderate | severe — only when detected
    evidence: str                  # the measured numbers behind the conclusion


def _conf(value: float, minor: float, scale: float) -> float:
    """Confidence grows with how far the measurement exceeds the trigger."""
    return round(min(CONF_CAP, max(CONF_FLOOR, CONF_FLOOR + scale * (value - minor))), 2)


def _severity(value: float, th: dict) -> str:
    if value >= th["severe"]:
        return "severe"
    if value >= th["moderate"]:
        return "moderate"
    return "minor"


def _finding(name, label, status, confidence=None, severity=None, evidence="") -> DefectFinding:
    return DefectFinding(name=name, label=label, status=status,
                         confidence=confidence, severity=severity, evidence=evidence)


def detect_defects(f: OnionFeatures, rules: dict) -> list[DefectFinding]:
    dr = rules.get("defect_rules", {})
    out: list[DefectFinding] = []

    # ---------- ROT / dark decay ----------
    r = dr.get("rot", {})
    th = r.get("thresholds", {"minor": 0.05, "moderate": 0.12, "severe": 0.22})
    if f.dark_region_ratio >= th["minor"]:
        out.append(_finding(
            "rot", "Rot / dark decay", "detected",
            confidence=_conf(f.dark_region_ratio, th["minor"], r.get("conf_scale", 6.0)),
            severity=_severity(f.dark_region_ratio, th),
            evidence=(f"dark regions cover {f.dark_region_ratio*100:.1f}% of the onion "
                      f"surface; {f.dark_spot_count} dark spot(s), largest covering "
                      f"{f.largest_spot_ratio*100:.1f}% (thresholds "
                      f"{th['minor']*100:.0f}/{th['moderate']*100:.0f}/{th['severe']*100:.0f}%)"),
        ))
    else:
        out.append(_finding(
            "rot", "Rot / dark decay", "not_detected",
            evidence=f"dark regions only {f.dark_region_ratio*100:.1f}% of surface "
                     f"(trigger {th['minor']*100:.0f}%)"))

    # ---------- SURFACE SPOTS ----------
    r = dr.get("surface_spots", {})
    min_cnt = int(r.get("min_spot_count", 3))
    min_big = float(r.get("min_largest_spot_ratio", 0.010))
    spots_hit = f.dark_spot_count >= min_cnt or f.largest_spot_ratio >= min_big
    if spots_hit and f.dark_region_ratio < th["minor"]:
        # spots but not enough dark area to call rot
        sev = "severe" if f.largest_spot_ratio >= 0.04 else (
              "moderate" if f.dark_spot_count >= min_cnt * 2 or f.largest_spot_ratio >= 0.02
              else "minor")
        out.append(_finding(
            "surface_spots", "Surface spots", "detected",
            confidence=_conf(max(f.dark_spot_count / max(1, min_cnt),
                                 f.largest_spot_ratio / min_big), 1.0,
                             r.get("conf_scale", 40.0) / 40.0),
            severity=sev,
            evidence=f"{f.dark_spot_count} distinct dark spot(s); largest = "
                     f"{f.largest_spot_ratio*100:.1f}% of onion area",
        ))
    elif not spots_hit:
        out.append(_finding(
            "surface_spots", "Surface spots", "not_detected",
            evidence=f"{f.dark_spot_count} spot(s) found, largest {f.largest_spot_ratio*100:.1f}% "
                     f"(triggers: ≥{min_cnt} spots or ≥{min_big*100:.0f}% single spot)"))

    # ---------- PHYSICAL DAMAGE / CUTS (skin-break texture) ----------
    r = dr.get("physical_damage", {})
    th = r.get("thresholds", {"minor": 0.06, "moderate": 0.10, "severe": 0.16})
    if f.edge_density >= th["minor"]:
        out.append(_finding(
            "physical_damage", "Cuts / bruise texture", "detected",
            confidence=_conf(f.edge_density, th["minor"], r.get("conf_scale", 8.0)),
            severity=_severity(f.edge_density, th),
            evidence=f"internal skin-edge density {f.edge_density*100:.1f}% "
                     f"(thresholds {th['minor']*100:.0f}/{th['moderate']*100:.0f}/"
                     f"{th['severe']*100:.0f}%)",
        ))
    else:
        out.append(_finding(
            "physical_damage", "Cuts / bruise texture", "not_detected",
            evidence=f"skin-edge density {f.edge_density*100:.1f}% (trigger {th['minor']*100:.0f}%)"))

    # ---------- SPROUTING ----------
    r = dr.get("sprouting", {})
    th = r.get("thresholds", {"minor": 0.015, "moderate": 0.05, "severe": 0.12})
    if f.green_top_ratio >= th["minor"]:
        out.append(_finding(
            "sprouting", "Sprouting", "detected",
            confidence=_conf(f.green_top_ratio, th["minor"], r.get("conf_scale", 7.0)),
            severity=_severity(f.green_top_ratio, th),
            evidence=f"green pixels occupy {f.green_top_ratio*100:.1f}% of the neck band "
                     f"(thresholds {th['minor']*100:.1f}/{th['moderate']*100:.0f}/"
                     f"{th['severe']*100:.0f}%)",
        ))
    else:
        out.append(_finding(
            "sprouting", "Sprouting", "not_detected",
            evidence=f"green in neck band {f.green_top_ratio*100:.1f}% "
                     f"(trigger {th['minor']*100:.1f}%)"))

    # ---------- DISCOLORED (colour uniformity, circular hue std) ----------
    r = dr.get("discolored", {})
    th = r.get("thresholds", {"minor": 14, "moderate": 20, "severe": 28})
    if f.hue_circular_std_deg >= th["minor"]:
        out.append(_finding(
            "discolored", "Discoloured / two-tone skin", "detected",
            confidence=_conf(f.hue_circular_std_deg, th["minor"], r.get("conf_scale", 0.05)),
            severity=_severity(f.hue_circular_std_deg, th),
            evidence=f"colour spread (circular hue std) {f.hue_circular_std_deg:.0f}° "
                     f"around mean hue {f.hue_circ_mean_deg:.0f}°",
        ))
    else:
        out.append(_finding(
            "discolored", "Discoloured / two-tone skin", "not_detected",
            evidence=f"colour spread {f.hue_circular_std_deg:.0f}° (trigger {th['minor']}°)"))

    # ---------- DEFORMED (shape) ----------
    r = dr.get("deformed", {})
    ct = r.get("circularity", {"minor": 0.86, "moderate": 0.78, "severe": 0.68})
    st = r.get("solidity", {"minor": 0.90, "moderate": 0.85, "severe": 0.78})
    shape_dev = max(
        (ct["minor"] - f.circularity) / ct["minor"] if f.circularity < ct["minor"] else 0.0,
        (st["minor"] - f.solidity) / st["minor"] if f.solidity < st["minor"] else 0.0,
    )
    if shape_dev > 0:
        sev = ("severe" if f.circularity < ct["severe"] or f.solidity < st["severe"]
               else "moderate" if f.circularity < ct["moderate"] or f.solidity < st["moderate"]
               else "minor")
        out.append(_finding(
            "deformed", "Deformed shape", "detected",
            confidence=_conf(shape_dev, 0.0, r.get("conf_scale", 4.0)),
            severity=sev,
            evidence=f"circularity {f.circularity:.2f} (ok ≥{ct['minor']:.2f}), "
                     f"solidity {f.solidity:.2f} (ok ≥{st['minor']:.2f}), aspect {f.aspect_ratio:.2f}",
        ))
    else:
        out.append(_finding(
            "deformed", "Deformed shape", "not_detected",
            evidence=f"circularity {f.circularity:.2f}, solidity {f.solidity:.2f} — within shape rules"))

    # ---------- UNDERSIZED — honesty showcase ----------
    out.append(_finding(
        "undersized", "Undersized", "insufficient_evidence",
        evidence=("Diameter measured only in pixels "
                  f"({f.equivalent_diameter_px:.0f}px, {f.area_fraction*100:.0f}% of frame). "
                  "No physical size reference is calibrated, so an under-size claim "
                  "cannot be made from this image. Calibrate with a coin/ArUco marker "
                  "to enable mm-based size rules.")))

    # ---------- INTERNAL QUALITY — the required honesty statement ----------
    out.append(_finding(
        "internal_quality", "Internal rot / sponginess", "insufficient_evidence",
        evidence=("Internal quality cannot be reliably determined from this image alone. "
                  "External inspection cannot see internal defects.")))

    return out


def predicted_class(findings: list[DefectFinding], rules: dict) -> tuple[str, float]:
    """Map detected defects → dataset class label (used by the evaluation page).
    Priority: rot > sprouting > damage > deformed > discolored."""
    mapping = rules.get("defect_to_class", {})
    priority = ["rot", "sprouting", "physical_damage", "deformed", "discolored", "surface_spots"]
    for name in priority:
        for x in findings:
            if x.name == name and x.status == "detected":
                return mapping.get(name, name), float(x.confidence or 0.0)
    return "healthy", 0.0


def findings_to_dicts(findings: list[DefectFinding]) -> list[dict]:
    return [asdict(x) for x in findings]
