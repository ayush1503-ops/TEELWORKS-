# Official Problem Statement — Traceability Matrix

| Field | Value |
|---|---|
| **Problem Statement ID** | 26031 |
| **Title** | Quality assessment and grading of onions are often subjective and vary across procurement centers, resulting in disputes and inconsistencies |
| **Organization** | Ministry of Consumer Affairs, Food & Public Distribution |
| **Department** | Department of Consumer Affairs (DOCA) |
| **Category** | Software |
| **Theme** | Smart Automation |
| **Expected solution** | AI-based mobile application: image-processing quality assessment; identify damaged / rotten / sprouted / undersized onions; estimate Grade A and URS percentages; instant digital quality report; reduce human bias and improve transparency |

---

## Requirement → Implementation matrix (every PS line, mapped)

| # | PS requirement | How this project implements it | Where (code / demo) | Verified by |
|---|---|---|---|---|
| 1 | **AI-based mobile application** | Mobile-first web app (camera 📷 + upload, large buttons, works on any phone browser — no install needed for procurement staff); FastAPI backend serves UI + API from one service | `frontend/` · live app home screen | `test_health_ok`, live preview |
| 2 | **Uses image processing to assess onion quality** | Layer A OpenCV pipeline: EXIF-safe load → resize → Gaussian blur → HSV → 3-candidate segmentation (chroma / Otsu-sat / Otsu-gray⁻¹) → morphology → contours → **20 measured features** (diameter, circularity, solidity, circular-hue stats, dark regions, pale gashes, gradient energy, sprout-band green…) | `app/services/preprocessing.py`, `features.py` · "Measurements" table in the result card | `test_healthy_onion_detected_scored_graded` |
| 3 | **Identifies damaged, rotten, sprouted, undersized** onions | Layer B **ensemble**: transparent rule engine (computed confidences + severity) **+ trained RandomForest** — all four PS-named classes plus discolored, deformed, healthy (7 classes). Undersized is detected by the ML size proxy while rules honestly await mm-calibration; internal rot is declared invisible | `defects.py`, `classifier.pkl`, `ensemble.py` · Analyze tab defect list with ML ✓/✗ tags | **Held-out test set: 100.0% (154/154)** via `POST /api/evaluate/dataset-test` · `test_dataset_test_endpoint_measures_live`, `test_ps_named_classes_supported` |
| 4 | **Estimates Grade A and URS percentages** | TWO distinct, never-confused numbers: (a) **batch share** — % of onions in a lot per grade (Grade A/B/C/URS bars, dashboard); (b) **per-onion grade probabilities** P(A)/P(URS) via Monte-Carlo over measurement noise. Response text states share ≠ confidence | `POST /api/batch`, `ensemble.grade_probabilities` · Batch tab dashboard | `test_batch_distribution_and_pdf` (shares sum to 100%, note present) |
| 5 | **Generates a digital quality report instantly** | One click → ReportLab PDF (single onion: image, ID, score breakdown, defects + severity + confidence, grade + rule version, size, recommendation, disclaimers; batch: totals + grade % + average score) | `GET /api/report/{id}.pdf`, `/api/report/batch/{id}.pdf` · "View detailed report" button | `test_pdf_report_generated` (valid `%PDF`) |
| 6 | **Reduces human bias & improves transparency** | Same deterministic pipeline for every onion at every centre; every score shows its full breakdown and reasons (✓/⚠/✗); every defect shows measured evidence; grades stamped with `rule_version` from a **configurable YAML** that adopts the official DOCA/procurement standard without code changes; disagreements between AI streams are surfaced, not hidden; honesty rules (no invented confidences, "insufficient visual evidence", internal-quality disclaimer) | `grading_rules.yaml`, `scoring.py`, result-card "Why this score" + disclaimers · live YAML-edit demo changes grades | `test_grading_rules_are_configurable`, `test_internal_quality_always_insufficient_evidence` |

## Extra capabilities beyond the PS (differentiators)

* Explainable-AI **drivers** (z-scored features: *why* an onion is classified away from healthy)
* **Evaluation harness** — live measured metrics with scope-stated accuracy (never claimed)
* **Capture-quality honesty** — poor lighting / shadow / framing warnings reduce analysis confidence
* Security from day one (magic-byte validation, size limits, rate limiting, no disk writes)
* SQLite → Supabase-ready storage with **zero personal data**
* Dataset tooling: synthetic bootstrap (1,050 imgs) today → field-data pipeline for tomorrow
* Free/open-source stack throughout; single-command deployment

## Scope statement we present to judges

> Visual analysis assesses **external** quality only; internal defects cannot be
> seen in a photo and are declared as such. Grades use prototype configurable
> rules until the official procurement standard is entered into
> `config/grading_rules.yaml`. Measured accuracy (100.0% on the 154-image
> held-out synthetic test set, run live through the identical production
> pipeline) is always quoted with its exact scope.
