# TEELWORKS — Onion Vision Lab (SIH PS 26031)

Visible-surface onion quality inspection prototype for the Department of
Consumer Affairs problem statement 26031.

**Current build (Phase 2):** the full stack lives in `onion-vision-lab/` inside this repo:

* **UI** — React 18 + TypeScript strict + Vite (5174) + Tailwind + Framer
  Motion + Three.js/R3F + jsPDF, designed in the style of the earlier ONION
  LAB project (light theme, glass cards, dot-grid backgrounds, electric-blue
  accents). One page: Navbar → Hero (3D onion + floating sensor cards) →
  Project story → How it works (4 steps) → Vision Lab (scanner with a LIVE
  on-device colour preview) → 3D Explorer (photo-textured onion + layer
  analysis + model-signal trace) → Metrics dashboard (live `/api/health`
  numbers with scopes) → Footer. Upload / live camera / sample tray photo →
  GREEN · YELLOW · RED verdicts in plain language → formal PDF report.
  Variety labels are per-onion colour ESTIMATES (red / golden / purple /
  white / unknown), never ground truth. Engines are swappable behind one
  contract (`OnionResult[]`) with a graceful local-DEMO fallback.
* **vision API** — FastAPI (8788): YOLOv8n single-class "onion" detector
  (ONNX, conf 0.45, letterbox **320** — size re-validated on VAL) →
  TensorFlow/Keras onion-vs-not-onion verifier gate → per-onion condition
  ensemble: **PyTorch** MobileNetV2 CNN (transfer learning) + **scikit-learn**
  calibrated RandomForest + HSV heuristic, fused by a logistic meta-learner.
  Measured on frozen test sets, plus a measured colour-shift stress test
  (single-variety honesty) — see `onion-vision-lab/vision-api/METRICS.md`.

Legacy material kept in this repo:

* `onion-grader/` — earlier FastAPI + OpenCV watershed + RandomForest
  prototype (per-onion grading, PDF reports; its own README/docs).
* `onion-lab/` — earlier static marketing/demo site.
* `scan_demo_52_onions.jpg` — the one real field photo; source of all
  training crops in the current build.

Honesty rules for the whole project: metrics are only ever quoted with their
scope (synthetic copy-paste from one field photo; field validation pending);
findings limited to Surface Discoloration / Surface Damage / Possible
Mold-Like Growth / Shriveling / Sprouting; confidence values are visual
prediction confidences, never food-safety probabilities; internal quality is
declared undeterminable — a camera cannot see inside an onion.
