# Onion Vision Lab — vision API (Phase 2)

FastAPI backend that turns ONE photo into an honest, per-onion
visible-condition inspection. **Phase 2 adds three real AI frameworks to the
Phase-1 stack — PyTorch, TensorFlow and scikit-learn — each with a real job,
all measured on frozen test sets.**

```
POST /api/analyze {imageBase64, sourceMode}  ->  OnionResult[]      (the UI contract)
GET  /api/health                             ->  ensemble status + honest metrics
```

## Pipeline

```
image (base64, in-memory only)
  └─> [1] Detector  YOLOv8n, single class "onion"      (ONNX runtime, conf 0.45, letterbox 320)
  └─> [2] Verifier  TF/Keras binary onion-vs-not-onion  (VAL-calibrated gate; ONNX serve)
  └─> [3] Condition per detected crop, THREE signals fused:
          • PyTorch MobileNetV2 CNN (transfer learning)  -> probs [clear, review, suspect]
          • scikit-learn RandomForest (calibrated)        -> probs over 26 HSV/texture features
          • HSV heuristic rules (Phase 1)                 -> cue scores
          fused by a multinomial LogisticRegression meta-learner (soft-probability stacking)
  └─> OnionResult[]: bbox + status vocabulary + findings + AI-INFERRED regions + cues + signals
```

Files: `app.py` (API) · `yolo_onnx.py` (detector) · `ensemble.py` (verifier +
condition fusion) · `condition.py` (heuristic + findings vocabulary guard) ·
`hsv_features.py` (single source of hand-crafted features) · `schemas.py`
(the OnionResult contract, mirrored by the UI's `src/types/vision.ts`).

## Measured results → see `METRICS.md`

Every number is measured on the frozen sets described there, with the scope
stated: crops come from **one field photo** (a 52-onion tray, cool lighting —
the onions read blue-purple in that photo, and the models are trained on those
actual pixels); scenes/damage/distractors are **programmatic synthetic**.
`GET /api/health` serves the same JSON the metrics document is rendered from.

## Models (`models/`)

| file | what |
|---|---|
| `onion-yolov8n.onnx` / `.pt` | single-class detector (served / retrainable) |
| `verifier.onnx` + `verifier_savedmodel/` | TF/Keras verifier (SavedModel artifact, ONNX at serve time) |
| `condition-cnn.onnx` | PyTorch MobileNetV2 condition head |
| `condition-rf.joblib` | calibrated RandomForest |
| `condition-meta-lr.joblib` | logistic meta-learner |
| `metrics.json` | all measured numbers (served by /api/health) |

If any Phase-2 artefact is missing at boot, the API degrades honestly to
whatever signals exist and says so in the response — it never fakes a signal.

## Run (serving)

```bash
cd vision-api
pip install -r requirements.txt
python3 -m uvicorn app:app --host 0.0.0.0 --port 8788
```

## Rebuild everything (CPU-only, 2 vCPU friendly)

```bash
pip install -r requirements-train.txt
# place the ImageNet backbone once (PyPI-only sandbox):
python3 -m pip download --no-deps fdet-offline-mobilenet-weights -d /tmp/fdet
cd /tmp/fdet && unzip -o *.whl && cp fdet_offline_mobilenet_weights/weights/mobilenet_v2-b0353104.pth \
    <repo>/onion-vision-lab/vision-api/train/phase2/pretrained/

cd train
python3 extract_crops.py            # 48 real crops from the field photo (watershed/grid)
python3 make_dataset.py             # v1: copy-paste scenes (520 train / 130 val)
python3 make_dataset2.py            # v2: +400 hard negatives, FREEZES the 170-image test set
python3 train_yolo.py               # YOLOv8n (from scratch in this sandbox - see METRICS.md)
python3 evaluate.py                 # frozen-set detection metrics -> metrics.json

cd phase2
python3 gen_condition_data.py       # synthetic damage labels (true by construction)
python3 train_condition_cnn.py      # PyTorch transfer learning -> condition-cnn.onnx
python3 train_verifier.py           # TF/Keras -> SavedModel + verifier.onnx + tau
python3 oof_cnn.py                  # out-of-fold CNN probs for honest stacking
python3 train_rf_meta.py            # sklearn RF + calibrated + logistic meta-fusion
python3 evaluate_verifier_gate.py   # gate ON vs OFF on the frozen detection set
python3 render_metrics.py           # -> ../METRICS.md
```

All training runs write logs (redirect stdout to a file — pipes can hide OOM
kills; every number in METRICS.md comes from these logged runs).

## Honesty rules encoded in this service

* Findings are limited to: **Surface Discoloration / Surface Damage / Possible
  Mold-Like Growth / Shriveling / Sprouting** — enforced in code, nothing else
  can be emitted.
* Status vocabulary: GREEN **NO OBVIOUS VISIBLE DAMAGE** · YELLOW **NEEDS
  REVIEW** · RED **VISIBLE DAMAGE**.
* Confidence = the model's **visual prediction confidence only**, never a
  probability that an onion is safe/unsafe to eat.
* A camera cannot see inside an onion: internal quality is declared
  unknowable in every response; 3D views show visible damage or clearly
  labelled **AI-INFERRED REGION**s.
* Frames are decoded in memory for the analyze call only — nothing is stored.

## Environment notes (this build)

* Sandbox network is restricted to PyPI/npm: COCO-pretrained YOLO weights and
  torchvision/Keras weight CDNs were unreachable, so (a) the detector was
  trained from scratch, and (b) the CNN backbone uses the official torchvision
  ImageNet checkpoint `mobilenet_v2-b0353104.pth` bundled inside the PyPI
  package `fdet-offline-mobilenet-weights` (kept in
  `train/phase2/pretrained/`). Both facts are stated in METRICS.md.
* `opencv-python-headless` is used (no libGL in the sandbox); install order
  matters if `ultralytics` pulls non-headless OpenCV.
* OpenCV 5 note: `cv2.watershed()` returns the markers — the extract script
  uses the return value.
