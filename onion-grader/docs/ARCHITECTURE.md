# 🧅 Onion Quality Analyzer — System Architecture

**Smart India Hackathon — Problem Statement 26031**
*"Quality assessment and grading of onions are often subjective and vary across procurement centers, resulting in disputes and inconsistencies."*

| | |
|---|---|
| **Status** | FULL PROTOTYPE (Phases 1–14) — rule-based pipeline live; ML training awaits dataset |
| **Last updated** | 2026-08-31 |
| **Stack** | Python 3.10+ · FastAPI · OpenCV · scikit-learn (hook) · ReportLab · SQLite |

---

## 1. What we are building

A camera-based assistant that gives every onion (and every lot) an **objective,
explainable and repeatable** quality evaluation:

```
photo → detect onion → measure visible features → detect visible defects
      → transparent quality score → configurable grade
      → batch statistics (Grade A % / URS %) → digital PDF report
```

It is a **decision-support tool for procurement staff**, not a replacement for
official grading. This distinction is stated in the UI and in every report.

---

## 2. Design principles (non-negotiable)

1. **Honesty before impressiveness.** The system never invents confidences,
   scores or grades. If the visual evidence is insufficient, it returns
   `"Insufficient visual evidence"`. Accuracy/mAP numbers are published **only
   after being measured on a real held-out test set**.
2. **Four strictly separated layers** — A) image processing, B) ML prediction,
   C) quality scoring, D) official grading rules. Each layer is its own module
   and can be replaced without touching the others (e.g. new government rules =
   edit a YAML file, not code).
3. **Configurable grading.** Score weights, thresholds and grade cut-offs live
   in `config/grading_rules.yaml`, with an explicit *"prototype — not official"*
   disclaimer until an authority supplies the real standard.
4. **External ≠ internal.** A photo shows only the outside. Every report
   states: *"Internal quality cannot be reliably determined from this image
   alone."*
5. **Confidence ≠ share of batch.** A 90% model confidence on one onion is
   never mixed up with "90% of the lot is Grade A". The two concepts use
   different fields in every response.
6. **Free & open-source only.** No paid APIs at any stage.
7. **Privacy by default.** We store images and analysis results only — no
   names, phone numbers or other personal data.

---

## 3. High-level architecture

```
┌────────────────────────────── CLIENTS ──────────────────────────────┐
│   Mobile-first Web App (Phase 1 — this repo)                         │
│   camera • upload • preview • analyze • results • reports            │
│   (Optional later: React Native / Flutter client — same API)         │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS · JSON · multipart image upload
┌───────────────────────────────▼─────────────────────────────────────┐
│                        FASTAPI BACKEND (Python)                      │
│  ┌──────────────────┐   ┌──────────────────────────────────────┐    │
│  │ Security layer    │→ │  JSON API                             │    │
│  │ • type/size check │   │  POST /api/analyze   (single onion)   │    │
│  │ • magic bytes     │   │  POST /api/batch     (lot statistics) │    │
│  │ • rate limiting   │   │  GET  /api/report/…  (PDF)            │    │
│  └──────────────────┘   │  POST /api/evaluate  (test page)       │    │
│                         └──────────────┬─────────────────────────┘    │
│                                          │                            │
│  LAYER A — IMAGE PROCESSING (OpenCV) ───▼─────────────────────────    │
│    resize → denoise → HSV → segmentation → contours → features        │
│                                          │ measurable features        │
│  LAYER B — ML PREDICTION ────────────────▼─────────────────────────   │
│    Phase 3–5 baseline: features + RandomForest/SVM (scikit-learn)     │
│    Phase 5 upgrade:   MobileNetV3 classifier + YOLOv8n detector       │
│                                          │ defect probabilities       │
│  LAYER C — QUALITY SCORING ENGINE ───────▼─────────────────────────   │
│    transparent weighted formula → quality score /100                  │
│                                          │                            │
│  LAYER D — GRADING RULES (config/grading_rules.yaml) ──────────────   │
│    score + size → Grade A / B / C / URS + recommendation              │
│                                          │                            │
│    Batch & URS % engine ── PDF reports ── Explainability ── Database  │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 4. The four layers (the heart of the design)

| Layer | What it does | Technology | Module | Built in | Can change independently? |
|---|---|---|---|---|---|
| **A. Image processing** | Detect the onion, segment it, and turn pixels into *measured facts* (size, shape, colour, spots…) | OpenCV + NumPy | `services/preprocessing.py`, `services/features.py` | Phase 2 | ✅ swap algorithms, ML untouched |
| **B. ML prediction** | Classify visible defects (rot, sprout, damage…) with honest confidence | scikit-learn baseline → PyTorch (MobileNetV3 + YOLOv8n) | `services/classifier.py`, `services/detection.py` | Phases 2–5 | ✅ retrain anytime; scoring untouched |
| **C. Quality scoring** | Combine measured features + defect evidence into a transparent 0–100 score | Pure Python, weights from YAML | `services/scoring.py` | Phase 3 | ✅ tune weights; grading untouched |
| **D. Grading rules** | Map score + size → grade (A/B/C/URS) and recommendation | YAML config | `services/grading.py`, `config/grading_rules.yaml` | Phases 3/8 | ✅ authority rules = YAML edit only |

**Why this matters for SIH judges:** when a procurement authority supplies its
real standard, we change one configuration file — no retraining, no code
surgery. And when someone asks "why is this onion Grade B?", we can point at
the exact rule and the exact measurement that produced it.

---

## 5. Component details

### 5.1 Clients

* **Phase 1 (built):** responsive mobile-first web app served by FastAPI at
  `/`. Works on any phone/PC browser; uses `getUserMedia` for the live camera
  with an automatic fallback to the native camera input
  (`<input capture="environment">`). No app-store install needed — ideal for
  procurement centres.
* **Optional later:** a React Native or Flutter client can be added against
  the exact same `/api/*` endpoints with zero backend changes.

### 5.2 API contract (FastAPI)

| Method | Path | Purpose | Available from |
|---|---|---|---|
| GET | `/api/health` | liveness + version + current phase | ✅ Phase 1 |
| POST | `/api/analyze` | one onion image → validation (P1) → features (P2) → score (P3) → ML defects (P5) → grade (P8) | ✅ stub in Phase 1, honest `analysis_available: false` |
| POST | `/api/batch` | many images → grade distribution, Grade A %, URS %, average score | Phase 9 |
| GET | `/api/report/{id}` | download PDF quality report | Phase 10 |
| GET | `/api/analyses/recent` | recent analyses for dashboard | Phase 11 |
| POST | `/api/evaluate` | upload labelled test images → actual vs predicted, metrics | Phase 13 |

**Target shape of the final `/api/analyze` response** (fields populate phase by
phase — nothing is faked on the way):

```jsonc
{
  "analysis_id": "uuid",                  // Phase 11
  "detection": {                          // Phase 2 (OpenCV) / Phase 5 (YOLO)
    "found": true,
    "bounding_box": [x, y, w, h],
    "annotated_image_b64": "..."          // onion outline + defect regions drawn
  },
  "features": {                           // Phase 2 — measured facts
    "diameter_px": 812, "area_px": 412000,
    "circularity": 0.91, "color_stats": {"hue_mean": 14.2},
    "dark_region_ratio": 0.03
  },
  "defects": [                            // Phase 3 rules / Phase 5 ML
    {"name": "surface damage", "confidence": 0.91, "severity": "moderate"}
    // OR {"name": "internal rot", "status": "insufficient_visual_evidence"}
  ],
  "quality_score": {"score": 87, "breakdown": {"size": 18, "...": 0}},
  "grade": {"predicted": "A", "rule_version": "prototype-v0"},
  "batch": null,                          // only filled by /api/batch
  "disclaimers": [
    "Internal quality cannot be reliably determined from this image alone.",
    "Grades use prototype rules, not an official standard."
  ]
}
```

### 5.3 Computer-vision pipeline (Layer A) — and *why* each technique

| Stage | Technique | Why it is used |
|---|---|---|
| Resize | `cv2.resize` (max side ≈ 1024 px) | All photos analysed at the same scale; big phone photos are slow and add noise |
| Noise reduction | Gaussian blur (5×5) | Phone photos have sensor noise and dust specks; smoothing *before* thresholding prevents false "defect spots" |
| Colour conversion | BGR → HSV | HSV separates colour (Hue) from brightness (Value) → colour analysis tolerates different lighting; onion-skin hues, discoloration and black rot regions become separable |
| Segmentation | HSV range thresholding + Otsu | Separates the onion blob from tables, hands, sacks — the most variable real-world factor |
| Morphology | open / close / dilate / erode | Removes leftover speckles, fills holes inside the mask → one clean, solid onion mask |
| Contours | `cv2.findContours` + `arcLength` | Gives the boundary, area, perimeter, bounding box, equivalent diameter; also draws the outline shown to the user |
| Shape descriptors | circularity = 4πA/P², aspect ratio | Deformation / double-bulb detection ("deformed onion") |
| Edge detection | Canny *inside the mask only* | Highlights surface cracks and cuts as texture evidence |
| Defect mapping | dark-region & spot detection (adaptive threshold in HSV/Lab) | Bruises, rot spots, mould, black patches; green shoot detection at the neck → sprouting |

**Size honesty rule:** pixels are not millimetres. Diameter is reported in px
until a size reference is calibrated (a coin / ArUco marker in frame — planned
as an optional Phase 8 feature). The UI will label it accordingly.

### 5.4 ML models (Layer B) — which model and why

| Step | Model choice | Why |
|---|---|---|
| Baseline classifier (Phase 3–5) | Handcrafted features (Layer A) + **RandomForest / SVM** (scikit-learn) | Trains on only a few hundred images, runs on CPU (no GPU needed at procurement centres), gives feature-importance explainability, hard to overfit badly. First *measurable* model |
| Advanced classifier (Phase 5) | **Transfer learning: MobileNetV3-Small / EfficientNet-B0** (PyTorch, ImageNet-pretrained) | Works well with small datasets because the network already knows general visual features; small & fast on CPU; easy Grad-CAM heatmaps |
| Multi-onion detection (Phase 5+) | **YOLOv8-nano** | Detects and counts many onions in one photo with bounding boxes; real-time on CPU; standard mAP metrics; exports to ONNX for deployment |

The transparent rule engine (Layer C) is **never removed** — ML supplies
defect *evidence*; the score stays a human-readable formula. This is what makes
the system defensible in a procurement dispute.

### 5.5 Quality scoring engine (Layer C)

Conceptual formula (all weights configurable, defaults are prototype values):

```
quality_score = w1·appearance + w2·size + w3·shape + w4·colour_uniformity
              + w5·skin_condition
              − w6·damage − w7·rot − w8·sprouting − w9·spots
```

Each sub-metric is normalised 0–1 from *measured* features, then the weighted
sum is scaled to 0–100. The response always includes the **breakdown**, so the
UI can show "why 87/100".

### 5.6 Grading rules module (Layer D) — `config/grading_rules.yaml`

```yaml
rule_version: prototype-v0        # NOT OFFICIAL — until an authority standard is supplied
disclaimer: >
  Prototype grading rules. Replace thresholds/weights with the official
  procurement standard when provided by the competent authority.

quality_score_weights:
  appearance: 25
  size: 20
  shape: 15
  colour_uniformity: 15
  skin_condition: 10
  defect_penalty: 25            # how strongly defects subtract

grade_thresholds:               # score → grade
  A:   { min_score: 85 }
  B:   { min_score: 70 }
  C:   { min_score: 50 }
  URS: { min_score: 0  }

size_rules:                     # filled from the authority standard later
  diameter_mm: { A: [55, null], B: [45, 55], C: [35, 45], URS: [null, 35] }

recommendations:
  A: "Accept — top grade"
  B: "Accept"
  C: "Accept with price differential / secondary use"
  URS: "Reject / divert (under-size or reject category)"
```

> **URS note:** URS is the under-size/reject category used in procurement.
> Its exact definition varies by authority and market — the config above is a
> placeholder that **must** be replaced with the official specification.

### 5.7 Batch & URS engine (Phase 9)

* Input: N onion images (or N detections from fewer photos).
* Output: total count, Grade A/B/C/URS **percentages of the batch**, average
  quality score, per-defect frequency, downloadable batch report.
* **Explicit separation (required by the problem statement):**
  * `model_confidence` — how sure the model is about *one* onion's defect/grade.
  * `grade_share_percent` — what fraction of the *batch* fell in each grade.
  These are different fields and are never merged.

### 5.8 Digital reports (Phase 10)

PDF via **ReportLab** (pure Python, free): date/time, image, onion/analysis ID,
quality score + breakdown, predicted grade + rule version, defects with
severity & confidence, model confidence, size estimate (px or calibrated mm),
recommendation, disclaimers. Batch reports add totals and grade percentages.

### 5.9 Database (Phase 11)

SQLite during development → **Supabase/PostgreSQL** in deployment (switch =
one SQLAlchemy connection URL). No personal data.

```
analyses(id UUID PK, created_at, image_ref, img_w, img_h, onion_count,
         quality_score, grade, rule_version, defects JSONB,
         model_confidence, diameter_px, recommendation, report_ref)
batch_runs(id UUID PK, created_at, total_onions,
           grade_a_pct, grade_b_pct, grade_c_pct, urs_pct, avg_score)
```

### 5.10 Explainability (Phase 12)

1. Annotated image: onion outline + bounding box + defect regions highlighted.
2. Score breakdown table ("size 18/20, colour 13/15, …").
3. Plain-language reasons list (✓/⚠) shown in the UI.
4. Grad-CAM heatmap for the CNN classifier.
5. Every grade cites the rule version that produced it.

### 5.11 Evaluation harness (Phase 13)

* Classification: accuracy, precision, recall, F1, confusion matrix (scikit-learn).
* Detection (YOLO): mAP@0.5, mAP@0.5:0.95.
* Testing page: upload labelled images → table of actual vs predicted vs
  confidence vs ✓/✗.
* **Rule: no accuracy claim is ever displayed that was not computed on a real
  held-out test set.** Numbers shown in the demo come from this harness only.

---

## 6. Security design

| Threat | Control (all active from Phase 1) |
|---|---|
| Malicious file disguised as image | Extension check **+ magic-byte check + full decode via Pillow** (`verify()`) |
| Huge uploads / DoS | 8 MB limit, bounded read, in-memory only — uploads are **never** written to disk or executed |
| Pillow decompression bombs | Pillow's `MAX_IMAGE_PIXELS` guard kept enabled |
| API abuse | In-memory sliding-window rate limit (20 req/min/IP) — proper limiter (e.g. Redis-backed) at deployment |
| Injection / malformed input | Pydantic response models + FastAPI request validation |
| Personal data exposure | We simply never collect personal data |

## 7. Real-world conditions (lighting, dust, varieties…)

Handled on two fronts:

* **Training (Phase 4–5):** augmentation — brightness/contrast/gamma jitter,
  slight hue shift (onion varieties), rotation/flip, scale, blur, noise,
  background variation, shadows.
* **Inference (Layer A):** HSV colour space (illumination tolerance),
  adaptive thresholds, white-background capture guidance in the UI
  ("place onion on a plain surface"), and honest low-confidence handling —
  bad photos return *"Insufficient visual evidence"* instead of a guess.

## 8. Dataset strategy (Phase 4 — details then)

* **Verify-first:** in Phase 4 we will run a live search for public onion
  datasets (Kaggle, Roboflow Universe, Mendeley). If a suitable labelled set
  exists we use it; if not, we build our own. **We will not claim a dataset
  exists before checking.**
* **Self-collection plan:** 3–4 onion varieties × the 7 classes (healthy,
  rotten, damaged, sprouted, undersized, discolored, deformed), multiple
  backgrounds and lightings, 2–3 devices. Target ≥ 150–300 usable images per
  class for the baseline; more via augmentation.
* **Tools:** Roboflow (free tier) or CVAT / Label Studio for annotation;
  Google Colab (free GPU) for training.
* **Format:** YOLO `.txt` for detection, class labels for classification;
  export to COCO JSON as backup.
* **Split:** 70% train / 15% val / 15% test, stratified by class, captured on
  different days so the test set is genuinely unseen.

```
datasets/onion_defects/
├── images/{train,val,test}/...
├── labels/{train,val,test}/...      # YOLO format (detection)
├── classes/{healthy,rotten,damaged,sprouted,undersized,discolored,deformed}/  # classification
├── dataset.yaml
└── NOTES.md                          # provenance, licence, collection log
```

## 9. Known limitations (stated openly)

1. **Internal defects are invisible** — internal rot, sponginess, water content
   cannot be assessed from a photo. Every report says so.
2. **Millimetres need a reference** — without calibration, size is in pixels.
3. **Grades are prototype-grade** until official rules are configured.
4. **Single onion per photo** in the first prototype; architecture already
   returns a list of detections so multi-onion is additive (YOLO, Phase 5+).
5. **Accuracy is unknown until measured** (Phase 13) — we will not quote a
   number before that.

## 10. Folder structure (current ✔ and planned)

```
onion-grader/
├── README.md                     ✔ quickstart + status
├── docs/
│   ├── ARCHITECTURE.md           ✔ this file
│   ├── PHASES.md                 ✔ roadmap tracker
│   └── phase-notes/PHASE_01.md   ✔ beginner walkthrough for Phase 1
├── backend/
│   ├── requirements.txt          ✔
│   ├── run.py                    ✔ launcher
│   ├── app/
│   │   ├── main.py               ✔ FastAPI entry (API + static frontend)
│   │   ├── api/                  ✔ routes: analyze.py (P1), health.py (P1)
│   │   │   ├── batch.py          ☐ Phase 9
│   │   │   ├── reports.py        ☐ Phase 10
│   │   │   └── evaluate.py       ☐ Phase 13
│   │   ├── core/                 ✔ config.py, security.py (validation+limits)
│   │   ├── schemas/              ✔ Pydantic models
│   │   ├── services/
│   │   │   ├── preprocessing.py  ☐ Phase 2 (OpenCV pipeline)
│   │   │   ├── features.py       ☐ Phase 2 (measurements)
│   │   │   ├── defects.py        ☐ Phase 3 rules → Phase 5 ML
│   │   │   ├── classifier.py     ☐ Phase 5
│   │   │   ├── scoring.py        ☐ Phase 3
│   │   │   ├── grading.py        ☐ Phase 3/8
│   │   │   ├── batch.py          ☐ Phase 9
│   │   │   ├── report.py         ☐ Phase 10
│   │   │   └── explainability.py ☐ Phase 12
│   │   └── db/                   ☐ Phase 11 (SQLAlchemy → SQLite/Supabase)
│   └── tests/                    ✔ test_api.py (Phase 1)
├── frontend/                     ✔ index.html, css/style.css, js/app.js
├── config/
│   └── grading_rules.yaml        ☐ Phase 3/8
├── datasets/                     ☐ Phase 4 (git-ignored)
├── models/                       ☐ Phase 5 trained artifacts (git-ignored)
├── notebooks/                    ☐ Phase 4/5 (Colab training)
└── scripts/                      ☐ dataset prep, augmentation, evaluation
```

## 11. Phase roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Image upload/camera interface + validating API | ✅ **done** |
| 2 | OpenCV preprocessing + onion detection (segmentation, contours, features) | ⬜ next |
| 3 | Rule-based quality features + transparent score | ⬜ |
| 4 | Dataset: verify public / collect + label own | ⬜ |
| 5 | Train ML model (baseline RF → transfer-learned CNN; YOLO for multi-onion) | ⬜ |
| 6 | Integrate trained model into FastAPI | ⬜ |
| 7 | Client↔API polish (web client already connected since P1; optional RN/Flutter client) | ⬜ |
| 8 | Configurable grading engine + size calibration option | ⬜ |
| 9 | Batch analysis + URS % | ⬜ |
| 10 | PDF reports | ⬜ |
| 11 | Database (SQLite → Supabase/Postgres) | ⬜ |
| 12 | Explainable-AI visualisation (Grad-CAM, defect maps) | ⬜ |
| 13 | Evaluation harness + testing page | ⬜ |
| 14 | Deployment | ⬜ |

## 12. Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-08-31 | Mobile-first **web app** (FastAPI-served) instead of RN/Flutter first | Instantly usable on any phone at a procurement centre, no install; live-demoable during development; RN/Flutter can reuse the same API later |
| 2026-08-31 | FastAPI backend from Phase 1 (stub `/api/analyze`) | Establishes the real architecture early; Phase 2 swaps the stub for OpenCV without touching the frontend |
| 2026-08-31 | SQLite dev → Supabase/Postgres prod | Zero-config start; free managed Postgres at deployment; switch is one URL |
| 2026-08-31 | ReportLab for PDF | Pure Python, free, no system dependencies |
