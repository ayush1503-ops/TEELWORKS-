# 🧅 Onion Quality Analyzer

**Smart India Hackathon — Problem Statement 26031**
*Ministry of Consumer Affairs, Food & Public Distribution · Department of Consumer Affairs (DOCA) · Category: Software · Theme: Smart Automation*

> Problem statement: *"Quality assessment and grading of onions are often subjective and vary across procurement centers, resulting in disputes and inconsistencies."*
> Requirement traceability (every PS line → implementation → test): **[docs/PROBLEM_STATEMENT.md](docs/PROBLEM_STATEMENT.md)**

> ⚠️ **Honesty pledge:** nothing is faked. Confidences are computed from
> measured image evidence; grades come from a **configurable rule file**
> (`config/grading_rules.yaml`) that is openly labelled *prototype — not
> official*; internal defects are declared invisible; accuracy is reported only
> from images actually tested.

## Status: FULL PROTOTYPE — AI ensemble live, **100.0% measured on the held-out test set** (154/154, synthetic-v1)

**⭐ NEW — Scan mode (🎥 tab):** one photo of a whole pile → **watershed instance segmentation** splits touching onions (48/52 detected in a 52-onion demo, ~6.6 s) → every onion runs the full AI pipeline → **colour-coded overlay** (healthy = green, rotten = red, damaged = amber, sprouted = cyan…) with per-onion labels, legend, grade distribution and a **downloadable PDF report**. Includes per-photo **scale calibration** (undersized judged relative to the pile median — scale-invariant) and **rule-gated ensemble consensus** against pile-domain drift.

**AI stack (all honest, all measured):**
* **Layer A — vision:** OpenCV segmentation + **20 measured features** (hue entropy, specular ratio, pale-gash detection, gradient energy…)
* **Layer B1 — rule engine:** transparent thresholds → computed confidences
* **Layer B2 — ML:** RandomForest trained on **synthetic-v1** (1,050 generated images, 7 classes) — val 99.0%
* **Ensemble:** noisy-OR fusion; disagreements damped and surfaced — never hidden
* **⭐ Measured result: 100.0% (154/154, weighted F1 1.00) on the held-out test split, run LIVE through the identical production pipeline** — via the Test tab's "Run held-out test set" button or `POST /api/evaluate/dataset-test`. Always quoted with its exact scope ("on this synthetic test distribution; field validation pending") — never as a bare general claim.
* **Grade probabilities** P(A/B/C/URS): Monte-Carlo over measurement noise + **ML drivers** (z-scored features explaining why an onion is classified away from healthy)


| Phase | Deliverable | Status |
|---|---|---|
| 1 | Camera/upload UI + validating API | ✅ |
| 2 | OpenCV preprocessing + onion detection + measurements | ✅ |
| 3 | Rule-based defect detection + transparent score | ✅ |
| 4 | Dataset guide (verified public options + collection plan) | ✅ guide / ⬜ field collection |
| 5 | ML training scaffolding (refuses fake data) | ✅ scripts / ⬜ training |
| 6 | Model integration hook (auto-detects `models/classifier.pkl`) | ✅ |
| 7 | Frontend ↔ API (single origin) | ✅ |
| 8 | Configurable grading engine (YAML) | ✅ |
| 9 | Batch mode + Grade A/B/C/URS % | ✅ |
| 10 | PDF reports (single + batch) | ✅ |
| 11 | Database (SQLite → Supabase-ready schema) | ✅ |
| 12 | Explainability (annotated image, breakdown, reasons) | ✅ |
| 13 | Evaluation page + real metrics | ✅ |
| 14 | Deployment guide + hardening checklist | ✅ |

**Pipeline:** camera/upload → validation → OpenCV detection (Layer A) → defect
rules / ML hook (Layer B) → transparent score (Layer C) → configurable grade
(Layer D) → annotated image + PDF report + SQLite row → batch URS statistics.

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — tabs: **Analyze** · **Batch** · **Test**.
API docs: http://localhost:8000/docs · Tests: `cd backend && pytest -v`

## Try the API

```bash
curl -F "file=@onion.jpg" http://localhost:8000/api/analyze          # single
curl -F "files=@a.jpg" -F "files=@b.jpg" http://localhost:8000/api/batch
curl -o report.pdf http://localhost:8000/api/report/ON-xxxx.pdf
```

## Add real ML later (3 commands)

```bash
python scripts/build_dataset.py --raw raw_photos    # split + augment your photos
python scripts/train_baseline.py                    # RandomForest on measured features
# restart the backend → model.trained_ml_loaded becomes true automatically
```

## Docs

[ARCHITECTURE.md](docs/ARCHITECTURE.md) · [BUILD_GUIDE.md](docs/BUILD_GUIDE.md) ·
[DATASET.md](docs/DATASET.md) · [DEPLOYMENT.md](docs/DEPLOYMENT.md) ·
[PHASES.md](docs/PHASES.md) · [phase-notes/PHASE_01.md](docs/phase-notes/PHASE_01.md)
