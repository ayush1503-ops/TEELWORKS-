# BUILD GUIDE — every phase, what/why/how (beginner-friendly)

One page per phase-group. For each: **what we built · why · where it lives ·
how to run/test it · common errors**.

---

## Quickstart (whole project)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 → three tabs: **Analyze** · **Batch** · **Test**.
API docs: http://localhost:8000/docs · Tests: `pytest -v`

---

## Phase 1 — Image input UI + validating API ✅
* **What/Why:** camera/upload → preview → analyze; security from day one.
* **Where:** `frontend/` (index.html, css, js) · `app/api/analyze.py` · `app/core/security.py`.
* **Test:** `pytest -v` (validation tests); upload a `.txt` renamed to `.jpg` → rejected 415.
* **Errors:** `ModuleNotFoundError: app` → run from `backend/`; camera blocked → app falls back to native camera input automatically.

## Phase 2 — OpenCV preprocessing + onion detection ✅
* **What:** resize → Gaussian blur → HSV → 3 candidate masks (chroma / Otsu-saturation / Otsu-gray) → morphology → largest solid contour → measurements (area, perimeter, circularity, solidity, hue stats via **circular mean** so red onions don't average to cyan).
* **Why each:** blur kills phone noise before thresholds; HSV separates colour from lighting; three masks because red/pink/white onions defeat any single threshold; morphology cleans speckles/holes.
* **Where:** `app/services/preprocessing.py`, `app/services/features.py`.
* **Test:** `pytest -v` (synthetic onion detected; blank image honestly "not detected").
* **Errors:** "No onion detected" on busy backgrounds → re-take on a plain contrasting surface (the app says this too).

## Phase 3 — Rule-based defect analysis + transparent score ✅
* **What:** six measured-evidence defects (rot, spots, damage, sprouting, discolored, deformed) + two **insufficient_evidence** entries (undersized — no mm calibration; internal quality — invisible). Score = Σ components − Σ severity-weighted penalties; full breakdown returned.
* **Confidences are computed**, e.g. `conf = 0.5 + 6 × (dark_ratio − 0.05)`, capped 0.95 — from measurement magnitude, never invented.
* **Where:** `app/services/defects.py`, `app/services/scoring.py`.
* **Test:** synthetic healthy vs rotten onion → healthy scores higher (in pytest).

## Phase 4 — Dataset ✅ (guide) / ⬜ (collection is your field work)
* Verified: no adequate public bulb dataset (261-image rot/sprout set exists — details in `docs/DATASET.md`). Collect → label by folder → `scripts/build_dataset.py` (70/15/15 + augmentation).

## Phase 5 — ML training ✅ (synthetic bootstrap) / ⬜ (field data)
* **Done now:** `scripts/generate_synthetic_dataset.py` builds a labelled synthetic set (7 classes × 90, randomized varieties/backgrounds/lighting/defects) → `scripts/train_baseline.py --dataset datasets/synthetic_v1 --label synthetic-v1` trains the RandomForest on the SAME 18 measured features the rules use. **Measured: 97.8% validation accuracy on the synthetic distribution** — quoted ONLY as that, everywhere, with "field validation pending" stamped next to it.
* **Ensemble (new):** `app/services/ensemble.py` — noisy-OR fusion of rule + ML confidences per defect; when the streams disagree, confidence is damped and flagged ("streams disagree"). **Grade probabilities** P(A/B/C/URS) come from Monte-Carlo over realistic measurement noise (±15–30% per feature, 180 trials, deterministic seed).
* **Field data later:** collect → `build_dataset.py --raw raw_photos` → `train_baseline.py --dataset datasets/onion_defects --label field-v1` → the pkl replaces synthetic; every label in the API updates automatically.
* Advanced path (Colab, free GPU): MobileNetV3 classifier + YOLOv8n multi-onion detector — reasons in `docs/ARCHITECTURE.md` §5.4.

## Phase 6 — Model integration ✅ (hook built)
* `app/services/classifier.py` loads `models/classifier.pkl` if present; rules remain the explainable fallback. No model → response honestly says `rule_based_v1`.

## Phase 7 — Frontend ↔ API ✅
* One origin (FastAPI serves the frontend): no CORS problems; a React Native/Flutter client can call the same `/api/*`.

## Phase 8 — Configurable grading engine ✅
* **Where:** `config/grading_rules.yaml` + `app/services/grading.py`. Grade = f(score) by thresholds; optional mm size rules once `calibrated: true`. Every result stamps `rule_version` + disclaimer. **Change the YAML → grades change (tested in pytest).**
* mm calibration (optional add-on): photograph the onion next to a ₹1 coin (known ⌀) or printed ArUco marker, compute px→mm, set `calibrated: true`.

## Phase 9 — Batch & URS ✅
* `POST /api/batch` (≤25 files) → distribution Grade A/B/C/URS **share of batch**, avg score, defect tally, per-onion list, PDF. The response explicitly separates batch share from per-onion confidence.

## Phase 10 — PDF reports ✅
* `GET /api/report/{id}.pdf`, `GET /api/report/batch/{id}.pdf` — ReportLab; includes image, score breakdown, defects+severity+confidence, rule version, size, recommendation, disclaimers.

## Phase 11 — Database ✅ (SQLite dev)
* `app/services/database.py` — `analyses`, `batch_runs`, `eval_results`. No personal data — only analysis facts + small processed thumbnails. Production: same schema → Supabase/PostgreSQL via SQLAlchemy.

## Phase 12 — Explainability ✅ (level 1–3)
* Annotated image (onion outline, bbox, defect regions, sprout zone) · score breakdown table · plain-language reasons ✓/⚠/✗ · rule_version stamping. Grad-CAM is unlocked when the CNN exists (Phase 5).

## Phase 13 — Testing & evaluation ✅
* Test tab → upload labelled image → actual vs predicted vs confidence vs correct/incorrect. `GET /api/evaluate/metrics` → accuracy, weighted P/R/F1, per-class, confusion matrix — computed **only** from images actually run.
* **⭐ Held-out test demo:** `POST /api/evaluate/dataset-test` (Test-tab button) runs the untouched test split through the **identical production pipeline** and measures accuracy live. **Measured: 100.0% (154/154, weighted F1 1.00) on synthetic-v1's held-out split** — always displayed with its scope: "on this test distribution; field validation pending".

## Phase 14 — Deployment ✅ (docs) 
* `docs/DEPLOYMENT.md` — free hosting options + production hardening list.

---

## The 10 most common errors (all phases)

| Error | Fix |
|---|---|
| `ModuleNotFoundError: app` | run uvicorn/pytest from `backend/` |
| `Form data requires python-multipart` | `pip install -r requirements.txt` |
| 413 upload | image > 8 MB (`core/config.py`) or batch > 25 |
| 415 upload | not a real JPG/PNG (magic-byte check) |
| 429 | rate limit 30/min/IP — wait or tune config |
| "No onion detected" | plain contrasting background, even light, one onion |
| Score seems low on a good onion | check the reasons list — usually shadows/poor lighting flagged; retake |
| PDF blank images | very old analyses before thumbnails existed |
| Grade didn't change after editing YAML | cache refreshes ≤5 s — retry |
| Camera doesn't open in preview iframe | app auto-falls back to native camera; or open the URL directly |
