"""Full-system tests — Onion Quality Analyzer (all phases).

Run from backend/:  pytest -v

Covers:
  * security (fake/wrong/empty/oversized/rate-limit)
  * OpenCV pipeline on SYNTHETIC onions (healthy / rotten / sprouted / blank)
  * honest no-detection behaviour
  * defect detection driven by real measurements (rot on the rotten one)
  * transparent scoring (healthy scores above rotten)
  * configurable grading (changing thresholds changes the grade)
  * batch endpoint + distribution maths
  * PDF generation (%PDF magic bytes)
  * database persistence
  * evaluation endpoint + metrics
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from app.core import security  # noqa: E402
from app.main import app  # noqa: E402
from app.services import database as db  # noqa: E402
from app.services import features as fe, preprocessing as pre  # noqa: E402
from app.services.grading import assign_grade, load_rules  # noqa: E402

client = TestClient(app)


# ------------------------------------------------------------------ #
# Synthetic onion factory (deterministic, drawn with PIL)             #
# ------------------------------------------------------------------ #
def synth_onion(kind: str = "healthy") -> bytes:
    img = Image.new("RGB", (640, 640), (205, 200, 190))          # plain light bg
    d = ImageDraw.Draw(img)
    cx, cy, r = 320, 350, 190
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(150, 60, 42))   # onion body
    for i in range(3):                                                # subtle skin streaks
        d.arc([cx - r + 12 + 10 * i, cy - r + 18, cx + r - 12 - 10 * i, cy + r - 18],
              start=200, end=340, fill=(138, 54, 38), width=5)
    if kind == "rotten":                                              # big dark soft patches
        d.ellipse([cx - 100, cy + 10, cx + 20, cy + 100], fill=(40, 18, 14))
        d.ellipse([cx + 30, cy - 80, cx + 125, cy - 10], fill=(46, 20, 15))
    if kind == "sprouted":                                            # green shoot at the neck
        d.polygon([(cx - 9, cy - r + 8), (cx + 9, cy - r + 8), (cx, cy - r - 58)],
                  fill=(58, 158, 58))
        d.ellipse([cx - 28, cy - r - 4, cx + 28, cy - r + 42], fill=(70, 172, 70))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def blank_image() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (640, 640), (255, 255, 255)).save(buf, format="JPEG")
    return buf.getvalue()


def post_analyze(content: bytes, filename: str = "onion.jpg"):
    return client.post("/api/analyze", files={"file": (filename, content, "image/jpeg")})


# ------------------------------------------------------------------ #
# 1) system + security                                                #
# ------------------------------------------------------------------ #
def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_fake_jpeg_rejected():
    r = post_analyze(b"definitely not an image")
    assert r.status_code == 415


def test_disallowed_extension_rejected():
    r = client.post("/api/analyze",
                    files={"file": ("onion.gif", synth_onion(), "image/gif")})
    assert r.status_code == 415


def test_empty_file_rejected():
    r = post_analyze(b"")
    assert r.status_code == 400


def test_oversized_file_rejected(monkeypatch):
    monkeypatch.setattr(security, "MAX_UPLOAD_BYTES", 1000)
    big = io.BytesIO()
    Image.new("RGB", (2000, 2000), (150, 60, 42)).save(big, format="JPEG")
    assert post_analyze(big.getvalue()).status_code == 413


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(security, "RATE_LIMIT_WINDOW_SECONDS", 60)
    security._request_log.clear()
    img = synth_onion()
    assert post_analyze(img).status_code == 200
    assert post_analyze(img).status_code == 200
    assert post_analyze(img).status_code == 429
    security._request_log.clear()


# ------------------------------------------------------------------ #
# 2) OpenCV pipeline on synthetic onions                              #
# ------------------------------------------------------------------ #
def test_healthy_onion_detected_scored_graded():
    r = post_analyze(synth_onion("healthy"))
    assert r.status_code == 200
    b = r.json()
    assert b["analysis_available"] is True
    assert b["detection"]["found"] is True
    assert b["detection"]["annotated_image_b64"]            # annotated image returned
    assert 0 <= b["quality_score"]["score"] <= 100
    assert b["grade"]["grade"] in {"A", "B", "C", "URS"}
    assert b["grade"]["rule_version"]                        # rule set stamped
    assert b["features"]["equivalent_diameter_px"] > 100     # real measurement
    assert 0 < b["analysis_confidence"]["value"] <= 0.95


def test_rotten_onion_rot_detected_with_computed_confidence():
    r = post_analyze(synth_onion("rotten"))
    b = r.json()
    rot = [d for d in b["defects"] if d["name"] == "rot"]
    assert rot and rot[0]["status"] == "detected"
    assert rot[0]["severity"] in {"minor", "moderate", "severe"}
    assert 0.5 <= rot[0]["confidence"] <= 0.95               # computed, not invented
    assert "%" in rot[0]["evidence"] or "dark regions" in rot[0]["evidence"]
    pred = b["predicted_class"]["label"]
    assert pred == "rotten"


def test_healthy_outscores_rotten():
    h = post_analyze(synth_onion("healthy")).json()["quality_score"]["score"]
    x = post_analyze(synth_onion("rotten")).json()["quality_score"]["score"]
    assert h > x


def test_sprouted_onion_sprouting_detected():
    b = post_analyze(synth_onion("sprouted")).json()
    spr = [d for d in b["defects"] if d["name"] == "sprouting"]
    assert spr and spr[0]["status"] == "detected"


def test_internal_quality_always_insufficient_evidence():
    b = post_analyze(synth_onion("healthy")).json()
    iq = [d for d in b["defects"] if d["name"] == "internal_quality"]
    assert iq and iq[0]["status"] == "insufficient_evidence"
    assert "cannot be reliably determined" in iq[0]["evidence"]


def test_blank_image_honest_no_detection():
    r = post_analyze(blank_image())
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "no_onion_detected"
    assert b["detection"]["found"] is False
    assert b["quality_score"] is None
    assert b["grade"]["grade"] == "UNDETERMINED"
    assert b["disclaimers"]                    # honesty statements present


# ------------------------------------------------------------------ #
# 3) scoring / grading units                                          #
# ------------------------------------------------------------------ #
def test_grading_rules_are_configurable():
    rules = load_rules()
    rules["grade_thresholds"]["A"]["min_score"] = 95          # stricter official rule
    assert assign_grade(85, True, rules)["grade"] == "B"
    rules["grade_thresholds"]["A"]["min_score"] = 80
    assert assign_grade(85, True, rules)["grade"] == "A"


def test_model_reporting_is_consistent_with_reality():
    """If a trained model file exists the API must say so (and what it was
    trained on); if not, it must honestly report rules-only."""
    from app.core.config import PROJECT_ROOT
    model_exists = (PROJECT_ROOT / "models" / "classifier.pkl").exists()
    b = post_analyze(synth_onion("healthy")).json()
    assert b["model"]["trained_ml_loaded"] is model_exists
    if model_exists:
        assert b["model"]["type"] == "rules+rf_ensemble"
        assert b["model"]["trained_on"]            # labelled training data
        assert b["model"]["validation_accuracy_on_training_dist"] is not None
        assert "FIELD VALIDATION IS PENDING" in " ".join(b["disclaimers"])
    else:
        assert b["model"]["type"] == "rule_based_v1"


def test_ensemble_fusion_and_disagreement_handling():
    from app.services.defects import DefectFinding
    from app.services.ensemble import fuse_findings
    rot = DefectFinding("rot", "Rot / dark decay", "detected", 0.9, "severe", "evidence")
    # model AGREEING (rotten 0.8) → fused ≥ each stream
    ens = fuse_findings([rot], {"predictions": [{"label": "rotten", "probability": 0.8}]})
    assert ens["predicted_class"] == "rotten"
    assert ens["agreement"] == "rules_and_model_agree"
    fused = ens["per_defect"]["rot"]["fused_confidence"]
    assert 0.9 <= fused <= 0.97
    # model DISAGREEING (healthy 0.9) → damped confidence + flag
    ens2 = fuse_findings([rot], {"predictions": [{"label": "healthy", "probability": 0.9}]})
    assert ens2["per_defect"]["rot"]["ml_supports"] is False
    assert ens2["per_defect"]["rot"]["fused_confidence"] < 0.9


def test_grade_probabilities_are_computed_and_sane():
    from app.services.defects import detect_defects
    from app.services.ensemble import grade_probabilities
    rules = load_rules()
    for kind in ("healthy", "rotten"):
        img = pre.load_bgr(synth_onion(kind))
        det = pre.segment_onion(img, rules)
        f = fe.extract_features(det, rules)
        findings = detect_defects(f, rules)
        gp = grade_probabilities(f, findings, rules)
        assert abs(sum(gp["probabilities"].values()) - 1.0) < 0.01   # a distribution
    # deterministic: same input → same output
    img = pre.load_bgr(synth_onion("healthy"))
    det = pre.segment_onion(img, rules)
    f = fe.extract_features(det, rules)
    findings = detect_defects(f, rules)
    assert (grade_probabilities(f, findings, rules)["probabilities"]
            == grade_probabilities(f, findings, rules)["probabilities"])


# ------------------------------------------------------------------ #
# 4) persistence + PDF                                                #
# ------------------------------------------------------------------ #
def test_analysis_saved_to_db():
    b = post_analyze(synth_onion("healthy")).json()
    row = db.get_analysis(b["analysis_id"])
    assert row is not None
    assert row["onion_found"] == 1
    assert row["grade"] == b["grade"]["grade"]


def test_pdf_report_generated():
    b = post_analyze(synth_onion("healthy")).json()
    r = client.get(f"/api/report/{b['analysis_id']}.pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 5000


def test_recent_analyses_endpoint():
    r = client.get("/api/analyses/recent?limit=5")
    assert r.status_code == 200
    assert "analyses" in r.json()


# ------------------------------------------------------------------ #
# 5) batch mode                                                       #
# ------------------------------------------------------------------ #
def test_batch_distribution_and_pdf():
    files = [("files", ("a.jpg", synth_onion("healthy"), "image/jpeg")),
             ("files", ("b.jpg", synth_onion("healthy"), "image/jpeg")),
             ("files", ("c.jpg", synth_onion("rotten"), "image/jpeg"))]
    r = client.post("/api/batch", files=files)
    assert r.status_code == 200
    b = r.json()
    assert b["onions_found"] == 3
    dist = b["distribution"]
    total_pct = sum(g["pct"] for g in dist.values())
    assert abs(total_pct - 100.0) < 0.31                      # shares sum to ~100
    assert dist["A"]["count"] + dist["B"]["count"] + \
           dist["C"]["count"] + dist["URS"]["count"] == 3
    assert "NOT model confidences" in b["note"]               # share ≠ confidence
    pdf = client.get(b["report_url"])
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_batch_rejects_too_many_files():
    files = [("files", (f"{i}.jpg", synth_onion(), "image/jpeg")) for i in range(26)]
    r = client.post("/api/batch", files=files)
    assert r.status_code == 413


# ------------------------------------------------------------------ #
# 6) evaluation                                                       #
# ------------------------------------------------------------------ #
def test_evaluate_rotten_image():
    r = client.post("/api/evaluate",
                    files={"file": ("rot.jpg", synth_onion("rotten"), "image/jpeg")},
                    data={"actual": "rotten"})
    assert r.status_code == 200
    b = r.json()
    assert b["predicted"] == "rotten" and b["correct"] is True
    assert b["confidence"] > 0.5


def test_evaluate_invalid_label_rejected():
    r = client.post("/api/evaluate",
                    files={"file": ("x.jpg", synth_onion(), "image/jpeg")},
                    data={"actual": "delicious"})
    assert r.status_code == 422


def test_dataset_test_endpoint_measures_live():
    """⭐ demo endpoint: held-out split → full production pipeline → live metrics."""
    import pytest
    from app.core.config import PROJECT_ROOT
    if not (PROJECT_ROOT / "datasets" / "synthetic_v1" / "classes" / "test").exists():
        pytest.skip("synthetic test split not present on this machine")
    r = client.post("/api/evaluate/dataset-test?dataset=synthetic_v1&limit_per_class=2")
    assert r.status_code == 200
    b = r.json()
    assert b["measured_live"] is True
    assert b["n_images"] >= 14                      # 7 classes × 2
    assert 0.0 <= b["metrics"]["accuracy"] <= 1.0
    assert "not a claim about arbitrary field photos" in b["note"]
    cm = b["metrics"]["confusion_matrix"]
    assert len(cm["labels"]) >= 7 and cm["matrix"]


def test_ml_drivers_present_when_model_exists():
    import pytest
    from app.core.config import PROJECT_ROOT
    if not (PROJECT_ROOT / "models" / "classifier.pkl").exists():
        pytest.skip("no trained model present")
    b = post_analyze(synth_onion("rotten")).json()
    ml = b["model"]["ml_predictions"]
    assert ml and ml.get("drivers_vs_healthy"), "explainability drivers expected"
    top = ml["drivers_vs_healthy"][0]
    assert top["feature"] and abs(top["z"]) > 0


def test_ps_named_classes_supported():
    """PS 26031 explicitly requires identifying damaged, rotten, sprouted and
    undersized onions — the classifier must cover all four (+ healthy)."""
    import pytest
    from app.services.classifier import load_classifier
    model, meta = load_classifier()
    if model is None:
        pytest.skip("no trained model present")
    labels = {str(x) for x in model.classes_}
    required = {"damaged", "rotten", "sprouted", "undersized", "healthy"}
    assert required.issubset(labels), f"PS-required classes missing: {required - labels}"


def synth_pile(n_healthy=9, n_rotten=3, n_sprouted=2, size=900) -> bytes:
    """A pile of touching onions (grid + jitter, some overlapping) for the scan API."""
    img = Image.new("RGB", (size, size), (208, 202, 192))
    d = ImageDraw.Draw(img)
    body = (66, 42, 152)
    specs = (["healthy"] * n_healthy) + (["rotten"] * n_rotten) + (["sprouted"] * n_sprouted)
    cols, r = 5, 78
    for i, kind in enumerate(specs):
        row, col = divmod(i, cols)
        cx = 100 + col * 175 + (18 if row % 2 else -10) + (30 if i % 5 == 0 else 0)
        cy = 120 + row * 250 + (10 if i % 3 else -14)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=body)
        d.arc([cx - r + 10, cy - r + 14, cx + r - 10, cy + r - 14], 200, 340,
              fill=(56, 34, 138), width=4)
        if kind == "rotten":
            d.ellipse([cx - 42, cy - 22, cx + 40, cy + 40], fill=(40, 18, 14))
            d.ellipse([cx - 10, cy - 60, cx + 50, cy - 18], fill=(46, 20, 15))
        if kind == "sprouted":
            d.polygon([(cx - 8, cy - r + 6), (cx + 8, cy - r + 6), (cx, cy - r - 46)],
                      fill=(58, 158, 58))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def test_scan_multi_onion_pile():
    """⭐ Scan mode: one photo of ~14 touching onions → instances + colours + PDF."""
    r = client.post("/api/scan", files={"file": ("pile.jpg", synth_pile(), "image/jpeg")})
    assert r.status_code == 200
    b = r.json()
    assert b["onions_found"] >= 10                      # watershed split the pile
    assert any(o["class"] == "rotten" for o in b["onions"])
    assert b["annotated_image_b64"]
    assert b["legend"]
    assert b["distribution"]["A"]["count"] + b["distribution"]["B"]["count"] \
        + b["distribution"]["C"]["count"] + b["distribution"]["URS"]["count"] \
        == b["onions_found"]
    # scale calibration: pile onions must not be mass-flagged 'undersized'
    cc = b["class_counts"]
    assert cc.get("undersized", 0) < b["onions_found"] / 2
    assert b["size_normalization"]["scale_factor"] > 0
    assert "may be merged or missed" in b["note"]       # honesty about counts
    pdf = client.get(b["report_url"])
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_scan_rejects_fake_image():
    r = client.post("/api/scan", files={"file": ("pile.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 415


def test_ps_grade_a_and_urs_percentages_present():
    """PS 26031 requires estimating Grade A and URS percentages — the batch
    response must carry both as shares of the batch."""
    files = [("files", ("a.jpg", synth_onion("healthy"), "image/jpeg")),
             ("files", ("b.jpg", synth_onion("rotten"), "image/jpeg"))]
    b = client.post("/api/batch", files=files).json()
    dist = b["distribution"]
    assert "A" in dist and "URS" in dist
    assert isinstance(dist["A"]["pct"], float) and isinstance(dist["URS"]["pct"], float)


def test_metrics_only_from_real_tests():
    r = client.get("/api/evaluate/metrics")
    assert r.status_code == 200
    b = r.json()
    if b["n"] == 0:
        assert b["metrics"] is None and "no accuracy is claimed" in b["note"]
    else:
        assert 0.0 <= b["metrics"]["accuracy"] <= 1.0
        assert "NOT a claim of general accuracy" in b["metrics"]["note"]
