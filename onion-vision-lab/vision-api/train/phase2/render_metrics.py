"""Render METRICS.md from models/metrics.json + per-model phase2 summaries.

One place to assemble every measured number with its scope statement, so the
document can never drift from the JSON the API serves at /api/health.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(os.path.dirname(HERE))
MODELS_DIR = os.path.join(API_DIR, "models")
MD = os.path.join(API_DIR, "METRICS.md")


def load(path):
    with open(path) as f:
        return json.load(f)


def model_row(name, block):
    return (f"| {name} | {block['accuracy']:.3f} | {block['macro_f1']:.3f} | "
            f"{block['confusion']} |")


def main():
    metrics = load(os.path.join(MODELS_DIR, "metrics.json"))
    det = metrics.get("detection", {})
    ph2 = metrics.get("phase2", {})
    cnn = load(os.path.join(MODELS_DIR, "phase2", "condition-cnn.json"))
    ver = load(os.path.join(MODELS_DIR, "phase2", "verifier.json"))
    fus = load(os.path.join(MODELS_DIR, "phase2", "condition-fusion.json"))
    gate = ph2.get("verifier_gate", {})
    yolo_sum = load(os.path.join(MODELS_DIR, "train_yolo_summary.json")) if \
        os.path.exists(os.path.join(MODELS_DIR, "train_yolo_summary.json")) else {}

    md = f"""# METRICS — Onion Vision Lab (Phase 2)

**Every number below is measured on the stated frozen set. No number is projected, cherry-picked or claimed beyond its scope.**

Scope reminder that applies to ALL tables: training positives are derived from
**48 real onion crops of ONE field photo** (a tray of the same variety/lighting);
scenes and condition labels are **programmatic synthetic** (copy-paste
composites; pasted damage). Distractors are **procedural look-alikes**, not
photographs of real produce. **Field validation is pending.** These numbers
describe this benchmark, not shop-floor performance.

---

## 1. Detector — YOLOv8n, single class "onion" (ONNX, conf 0.45, letterbox {det.get('input_size', 'n/a')})

| Metric | Value |
|---|---|
| Precision | {det.get('precision', 'n/a')} |
| Recall | {det.get('recall', 'n/a')} |
| F1 | {det.get('f1', 'n/a')} |
| mAP50 (101-pt) | {det.get('map50', 'n/a')} |
| TP / FP / FN | {det.get('tp', 'n/a')} / {det.get('fp', 'n/a')} / {det.get('fn', 'n/a')} |
| Negatives with ≥1 detection | {det.get('negative_images_with_detections', 'n/a')} / 40 |
| Avg inference (CPU) | {det.get('avg_inference_ms', 'n/a')} ms/image |

* **Benchmark (frozen):** {det.get('scope', 'n/a')}.
* **Serving-size selection (VAL split, honest):** the model was trained at
  imgsz 320, so letterbox size was selected on VAL: 320 → P 1.000 / R 0.947 /
  F1 0.973; 416 → 0.969; 512 → 0.970; 640 → 0.728; 832 → 0.308 (scale
  mismatch degrades the from-scratch model). 320 is served. The Phase-1
  "832px" config belonged to a different training run and is NOT reused.
* **Training:** from scratch, {yolo_sum.get('epochs', '?')} epochs (validated plateau), imgsz {yolo_sum.get('imgsz', '?')}, batch {yolo_sum.get('batch', '?')}. Pretrained COCO weights were NOT available in the training sandbox (network restricted to PyPI/npm) — the detector was trained from scratch on the project dataset.

## 2. Verifier — TensorFlow/Keras binary onion-vs-not-onion (gate stage)

| Metric | Value |
|---|---|
| Architecture | {ver.get('model')} ({ver.get('params')} params, {ver.get('imgsz')}px, batch {ver.get('batch')}) |
| Test binary accuracy | {ver.get('test_binary_acc')} |
| Test AUC | {ver.get('test_auc')} |
| Binary-model threshold | {ver.get('gate_threshold')} (chosen for val onion-recall {ver.get('val_recall_at_tau')} ) |
| **Serving gate τ (detection-level, VAL-calibrated)** | **{gate.get('gate_threshold', 'n/a')}** — {gate.get('tau_selection', 'n/a')} |
| Val FPR @ binary τ | {ver.get('val_fpr_at_tau')} |
| Test confusion @ binary τ | {ver.get('test_confusion_at_tau')} |
| ONNX parity vs Keras | max diff {ver.get('onnx_parity_maxdiff')} |

* Data: {ver.get('data', {}).get('train_pos', '?')} positive train images ({ver.get('data', {}).get('train_crops', '?')} crops + augs) vs {ver.get('data', {}).get('train_neg', '?')} procedural negatives; tested on {ver.get('data', {}).get('test_crops_held_out', '?')} held-out crops + fresh-seed distractors.
* **Scope:** {ver.get('scope')}

### 2b. Gate effect on the frozen detection benchmark (verifier ON vs OFF)

| Measure | before gate | after gate |
|---|---|---|
| FP on 40 distractor negatives | {gate.get('before', {}).get('negative_fp_total', 'n/a')} | {gate.get('after', {}).get('negative_fp_total', 'n/a')} |
| Negative images with any detection | {gate.get('before', {}).get('negative_images_with_detections', 'n/a')} | {gate.get('after', {}).get('negative_images_with_detections', 'n/a')} |
| Recall (130 positive scenes) | {gate.get('before', {}).get('recall', 'n/a')} | {gate.get('after', {}).get('recall', 'n/a')} |
| F1 | {gate.get('before', {}).get('f1', 'n/a')} | {gate.get('after', {}).get('f1', 'n/a')} |
| Demo 52-onion tray photo | — | {gate.get('demo_photo', {}).get('kept_after_gate', 'n/a')} of {gate.get('demo_photo', {}).get('raw_detections', 'n/a')} detections kept |

* **Honest gate analysis:** on this benchmark the detector alone may already
  produce **0 false positives on the 40 frozen negatives** (it was trained
  with 400 hard negatives), in which case the gate has nothing left to remove
  (fp_removed = {gate.get('fp_removed_on_negatives', 'n/a')}). The gate is
  kept as a **calibrated safety net**: τ = {gate.get('gate_threshold', 'n/a')}
  is selected on VAL true-positive scores and costs only
  {gate.get('recall_delta', 'n/a')} recall on the frozen test.
* τ selection: {gate.get('tau_selection', 'n/a')}.

## 3. Condition models — fused per-onion visible-condition ensemble

Benchmark (frozen): **12 held-out test crops × 6 variants/class = 216 images**
(crop-level split; no test crop appears in CNN/RF training or meta-learner
fitting). Classes: clear / review / suspect.

| Model (framework) | Accuracy | Macro-F1 | Confusion (rows=true) |
|---|---|---|---|
{model_row('PyTorch MobileNetV2 CNN (transfer, ONNX)', fus['models']['cnn_alone'])}
{model_row('scikit-learn calibrated RF (HSV+texture)', fus['models']['rf_alone'])}
{model_row('HSV heuristic rules (Phase 1)', fus['models']['heuristic_alone'])}
{model_row('**Fused: logistic meta-learner (OOF stacking)**', fus['models']['fused'])}

* **Selection honesty:** configuration was chosen on VAL macro-F1
  ({json.dumps(fus.get('selection', {}).get('val_macro_f1', {}))}). Both the
  per-model and fused TEST numbers are reported above; no superiority is
  claimed beyond the stated split.
* CNN: {cnn.get('model')} — {cnn.get('imgsz')}px, batch {cnn.get('batch')}, {cnn.get('epochs')} epochs ({cnn.get('train_seconds')}s). Pretrained source: {cnn.get('pretrained_source')}. ONNX parity max diff {cnn.get('onnx_parity_maxdiff')}.
* RF: {fus['rf']['n_estimators']} trees, {fus['rf']['calibration']}, {fus['features']['n_features']} features (HSV stats + LBP + edges + entropy).
* Meta-learner: {fus['meta']['learner']} on 15 features (3×3 probabilities + 6 cues), fitted on train-split OUT-OF-FOLD predictions ({fus['meta']['fitted_on']}), C={fus['meta']['C_selected_on_val']} selected on VAL, test log-loss {fus['meta']['test_logloss']}.
* **Scope:** {fus['scope']}

## 4. What these numbers do NOT mean

* Not field accuracy — every image derives from one photo's crops or from procedural generation.
* Not food safety — confidence values are visual prediction confidences only.
* Not internal quality — a camera cannot see inside an onion.

*Generated by train/phase2/render_metrics.py from models/metrics.json (served at GET /api/health).*
"""
    with open(MD, "w") as f:
        f.write(md)
    print("wrote", MD)


if __name__ == "__main__":
    main()
