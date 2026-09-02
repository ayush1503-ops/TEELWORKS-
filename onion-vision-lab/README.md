# 🧅 Onion Vision Lab (SIH PS 26031 — visible onion quality inspection)

Interactive onion inspection journey: **3D hero → SCAN (camera on-click /
upload drag-drop / sample photo) → multi-onion detection with animated tracking
circles → results dashboard → 3D inspection with pulsing AI-INFERRED REGIONs →
"why was this flagged" panel → PDF report.**

* **Frontend:** React 18 + TypeScript (strict) + Vite (port **5174**) + Tailwind
  + Framer Motion + Three.js / react-three-fiber + jsPDF.
* **Backend:** `vision-api/` (FastAPI on **8788**) — YOLOv8n single-class
  detector + TensorFlow verifier gate + fused condition ensemble
  (PyTorch CNN + sklearn RF + HSV heuristic behind a logistic meta-learner).
  See `vision-api/README.md` and `vision-api/METRICS.md` for measured numbers
  and their scope.

## One contract

Everything the UI renders flows through `src/types/vision.ts` →
`OnionResult[]`. Engines are swappable in `src/services/visionService.ts`:

* `VITE_VISION_API` (default `/vision-api`, proxied by Vite to `localhost:8788`)
  → **REMOTE INFERENCE API** (badge: LIVE).
* If the API is unreachable → graceful fallback to the in-browser HSV heuristic
  (**LOCAL DEMO**, amber badge, warning banner — never a silent fake).

## Run

```bash
npm install
npm run dev            # http://localhost:5174
# plus the API:
cd vision-api && pip install -r requirements.txt
python3 -m uvicorn app:app --host 0.0.0.0 --port 8788
```

`.env.local` sets `VITE_VISION_API=/vision-api` (an `.env.example` documents
it; the app works without it by using the same default).

## Browser e2e

```bash
node e2e/onion.e2e.mjs
```

Uploads the real 52-onion tray photo through the UI (expects results + engine
`REMOTE INFERENCE API` + zero page errors), then a distractor image (expects 0
detections), and checks the PDF report downloads. The sandbox has no
Playwright CDN access, so the script drives the `@sparticuz/chromium` binary.

## Honesty rules (enforced in UI + API)

* Camera permission is requested **only on click**; frames are processed
  in-memory for the analysis call and never stored or uploaded beyond it.
* DEMO/LIVE badges are truthful: LIVE = remote inference engine answered;
  DEMO = local fallback heuristic.
* Status vocabulary: GREEN `NO OBVIOUS VISIBLE DAMAGE` · YELLOW `NEEDS REVIEW`
  · RED `VISIBLE DAMAGE`. Findings limited to: Surface Discoloration / Surface
  Damage / Possible Mold-Like Growth / Shriveling / Sprouting.
* Confidence values are **visual prediction confidence**, not food-safety
  probabilities. A camera cannot see inside an onion — 3D views show visible
  damage or clearly-labelled AI-INFERRED REGIONs only.
