# Limitations — Onion Vision Lab v2

This document describes the honest scope, known limitations, and appropriate
use of the Onion Vision Lab v2 system. Read this before drawing any conclusions
from the model outputs.

---

## 1. Training Data Scope

| Aspect | Current scope |
|---|---|
| Source field photos | **1** (a single overhead tray photo of one variety/lighting condition) |
| Real onion crops extracted | 48 unique crops (train + val + test splits) |
| Synthetic scene generation | Programmatic copy-paste composites; pasted damage overlays |
| Distractor negatives | Procedural synthetic look-alikes — **not** photographs of real produce |
| Condition label source | Programmatic synthetic damage applied to real crops |
| Field validation | **Pending** — no shop-floor or multi-farm data has been collected |

All performance numbers in METRICS.md describe this benchmark, **not
shop-floor performance.**

---

## 2. What the Models Cannot Do

| Claim | Status |
|---|---|
| Determine **internal quality** | ❌ Impossible — a camera cannot see inside an onion |
| Certify food safety | ❌ Not a food-safety tool; do not use for human-consumption decisions |
| Generalise to unseen varieties | ⚠️ Unvalidated — only one variety/lighting has been tested |
| Generalise to different lighting | ⚠️ Unvalidated |
| Detect defects on the **underside** | ❌ Analysis is strictly limited to the visible surface in the image |
| Provide probabilistic food-safety confidence | ❌ Confidence values are visual prediction confidences, not safety probabilities |

---

## 3. Detection Pipeline Limitations

- **YOLOv8n trained from scratch** — pretrained COCO weights were unavailable
  during training (network-restricted sandbox); performance on out-of-distribution
  images may be lower than a COCO-pretrained baseline.
- **Input resolution:** letterbox 320 px. Very small onions in high-resolution
  images may not be detected reliably.
- **Max detections per image:** 64.
- **Max input image size:** 2 200 px on the longest side (images are downscaled
  before inference).
- **Confidence threshold:** 0.45 (fixed). Adjusting this value changes the
  precision/recall trade-off but has not been validated at other thresholds.

---

## 4. Verifier Gate Limitations

- The verifier was trained on **procedural synthetic negatives**, not photographs
  of real non-onion produce. Its false-positive rate on real-world distractors
  (e.g. garlic, shallots, potatoes) has not been measured.
- On the frozen benchmark the detector alone produced **0 false positives**;
  the gate therefore has nothing to remove in that scenario, and its real-world
  contribution is untested.

---

## 5. Condition / Defect Classification Limitations

- **Detectable findings are limited to:**
  - Surface Discoloration
  - Surface Damage
  - Possible Mold-Like Growth
  - Shriveling
  - Sprouting
- Conditions outside this list (bruising below skin, neck rot, fusarium) are
  **not** detected and will not appear as findings.
- The CNN (MobileNetV2, ImageNet transfer) was fine-tuned on **synthetic**
  damage overlays. Real-world defect textures differ.
- The RandomForest baseline operates on 26 HSV + texture features and performs
  significantly worse than the CNN alone (macro-F1 0.668 vs 0.912); the fused
  ensemble partially recovers this gap.
- Macro-F1 of the fused ensemble on the frozen test set: **0.894**. This is a
  benchmark figure, not a field accuracy estimate.

---

## 6. Performance & Cold-Start

- All inference is **CPU-only** in the standard deployment (Render free tier).
- First-request latency after a cold start is **30–60 seconds** while models
  load into memory.
- Render free instances **sleep after 15 minutes of inactivity**. The next
  request wakes the instance and triggers model re-loading.
- Approximate per-image inference time (warmed, CPU): 30–80 ms detect + 20–60 ms
  condition (varies by number of detections).

---

## 7. What the Confidence Values Mean

The `confidence` field on each `OnionResult` is a **composite visual prediction
score** — a product of the YOLO detector confidence and the condition ensemble
confidence, clamped to < 0.99. It reflects how certain the models are about
**their own visual predictions on the visible surface**, not:
- The probability that the onion is safe to eat
- The probability that the finding is correct in a production setting
- A statistical confidence interval

---

## 8. Appropriate Use

This tool is intended for:
- **Research and demonstration** of multi-model vision pipelines for agricultural
  inspection.
- **Educational exploration** of CV model limitations and honest benchmarking.

It is **not** intended for:
- Regulatory food-safety decisions
- Automated reject/accept sorting in commercial packing houses without additional
  field validation
- Any decision about human health

---

*See also: [METRICS.md](vision-api/METRICS.md) for full measured benchmark
tables and methodology.*

---

## 9. Variety & Colour

- The UI shows a per-onion variety chip (red / golden / purple / white /
  unknown). It is a **colour-family ESTIMATE from the visible skin**, never a
  cultivar identification and never ground truth.
- The models were trained on ONE variety/lighting. A colour-shift stress test
  (programmatic HSV re-colourings of the frozen test set) is measured and
  tabulated in METRICS.md section 2 — the out-of-family shift honestly fails
  (F1 drops and 10/40 negatives fire), which is exactly why generalising to
  unseen onion colours is **unvalidated**. Shallots and other alliums are not
  yet measured.
- A camera cannot tell white/cream onions from washed-out lighting reliably:
  low-saturation skin is decided by cream dominance, otherwise reported as
  UNKNOWN rather than guessed.
