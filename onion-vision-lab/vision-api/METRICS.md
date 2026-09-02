# METRICS — Onion Vision Lab (Phase 2)

**Every number below is measured on the stated frozen set. No number is projected, cherry-picked or claimed beyond its scope.**

Scope reminder that applies to ALL tables: training positives are derived from
**48 real onion crops of ONE field photo** (a tray of the same variety/lighting);
scenes and condition labels are **programmatic synthetic** (copy-paste
composites; pasted damage). Distractors are **procedural look-alikes**, not
photographs of real produce. **Field validation is pending.** These numbers
describe this benchmark, not shop-floor performance.

---

## 1. Detector — YOLOv8n, single class "onion" (ONNX, conf 0.45, letterbox 320)

| Metric | Value |
|---|---|
| Precision | 0.9974 |
| Recall | 0.9267 |
| F1 | 0.9607 |
| mAP50 (101-pt) | 0.9901 |
| TP / FP / FN | 379 / 1 / 30 |
| Negatives with ≥1 detection | 0 / 40 |
| Avg inference (CPU) | 17.7 ms/image |

* **Benchmark (frozen):** frozen synthetic copy-paste benchmark from ONE field photo (130 positive scenes from 9 held-out crops + 40 procedural distractor-only negatives); field validation pending.
* **Serving-size selection (VAL split, honest):** the model was trained at
  imgsz 320, so letterbox size was selected on VAL: 320 → P 1.000 / R 0.947 /
  F1 0.973; 416 → 0.969; 512 → 0.970; 640 → 0.728; 832 → 0.308 (scale
  mismatch degrades the from-scratch model). 320 is served. The Phase-1
  "832px" config belonged to a different training run and is NOT reused.
* **Training:** from scratch, 15 epochs (validated plateau), imgsz 320, batch 8. Pretrained COCO weights were NOT available in the training sandbox (network restricted to PyPI/npm) — the detector was trained from scratch on the project dataset.

## 2. Verifier — TensorFlow/Keras binary onion-vs-not-onion (gate stage)

| Metric | Value |
|---|---|
| Architecture | small CNN 4xConv+BN, binary onion/not-onion (406369 params, 96px, batch 8) |
| Test binary accuracy | 1.0 |
| Test AUC | 1.0 |
| Binary-model threshold | 0.5 (chosen for val onion-recall 1.0 ) |
| **Serving gate τ (detection-level, VAL-calibrated)** | **0.5** — min(0.5, 1st percentile of VAL true-positive p_onion scores); keeps 1.0 of 373 val TPs |
| Val FPR @ binary τ | 0.025 |
| Test confusion @ binary τ | {'tp': 80, 'fn': 0, 'fp': 0, 'tn': 80} |
| ONNX parity vs Keras | max diff 5.960464477539063e-08 |

* Data: 304 positive train images (38 crops + augs) vs 304 procedural negatives; tested on 10 held-out crops + fresh-seed distractors.
* **Scope:** held-out 10 real test crops x8 augs vs fresh-seed procedural distractors; negatives are SYNTHETIC look-alikes, not photographs of real produce

### 2b. Gate effect on the frozen detection benchmark (verifier ON vs OFF)

| Measure | before gate | after gate |
|---|---|---|
| FP on 40 distractor negatives | 0 | 0 |
| Negative images with any detection | 0 | 0 |
| Recall (130 positive scenes) | 0.9267 | 0.9267 |
| F1 | 0.9607 | 0.9607 |
| Demo 52-onion tray photo | — | 47 of 47 detections kept |

* **Honest gate analysis:** on this benchmark the detector alone may already
  produce **0 false positives on the 40 frozen negatives** (it was trained
  with 400 hard negatives), in which case the gate has nothing left to remove
  (fp_removed = 0). The gate is
  kept as a **calibrated safety net**: τ = 0.5
  is selected on VAL true-positive scores and costs only
  0.0 recall on the frozen test.
* τ selection: min(0.5, 1st percentile of VAL true-positive p_onion scores); keeps 1.0 of 373 val TPs.

## 3. Condition models — fused per-onion visible-condition ensemble

Benchmark (frozen): **12 held-out test crops × 6 variants/class = 216 images**
(crop-level split; no test crop appears in CNN/RF training or meta-learner
fitting). Classes: clear / review / suspect.

| Model (framework) | Accuracy | Macro-F1 | Confusion (rows=true) |
|---|---|---|---|
| PyTorch MobileNetV2 CNN (transfer, ONNX) | 0.912 | 0.912 | [[70, 2, 0], [13, 59, 0], [0, 4, 68]] |
| scikit-learn calibrated RF (HSV+texture) | 0.662 | 0.668 | [[40, 31, 1], [31, 40, 1], [4, 5, 63]] |
| HSV heuristic rules (Phase 1) | 0.444 | 0.350 | [[0, 45, 27], [0, 35, 37], [0, 11, 61]] |
| **Fused: logistic meta-learner (OOF stacking)** | 0.893 | 0.894 | [[67, 5, 0], [11, 61, 0], [0, 7, 65]] |

* **Selection honesty:** configuration was chosen on VAL macro-F1
  ({"cnn": 0.8295, "rf": 0.5991, "heuristic": 0.4137, "fused": 0.8411}). Both the
  per-model and fused TEST numbers are reported above; no superiority is
  claimed beyond the stated split.
* CNN: MobileNetV2 (ImageNet transfer) + 3-class head — 96px, batch 8, 8 epochs (174.4s). Pretrained source: torchvision mobilenet_v2-b0353104 bundled in PyPI package fdet-offline-mobilenet-weights (download.pytorch.org unreachable). ONNX parity max diff 1.7285346984863281e-06.
* RF: 300 trees, CalibratedClassifierCV(sigmoid, cv=3), 26 features (HSV stats + LBP + edges + entropy).
* Meta-learner: LogisticRegression(multinomial) on 15 features (3×3 probabilities + 6 cues), fitted on train-split OUT-OF-FOLD predictions (train-split OOF predictions (n=672; CNN 3-fold by crop via oof_cnn.py)), C=1.0 selected on VAL, test log-loss 0.2907.
* **Scope:** frozen 12 test crops, programmatic synthetic damage over real crops from ONE field photo; field validation pending

## 4. What these numbers do NOT mean

* Not field accuracy — every image derives from one photo's crops or from procedural generation.
* Not food safety — confidence values are visual prediction confidences only.
* Not internal quality — a camera cannot see inside an onion.

*Generated by train/phase2/render_metrics.py from models/metrics.json (served at GET /api/health).*
