# 🧅 Onion Vision Lab (SIH PS 26031 — visible onion quality inspection)

**Advanced inside, simple outside.** A camera-based quality inspection web app
for mandi workers, shopkeepers and consumers: point the camera → watch the
colours → tap once → get the verdict + report in plain language.

* **Frontend:** React 18 + TypeScript (strict) + Vite (port **5174**) +
  Tailwind + Framer Motion + Three.js / react-three-fiber + jsPDF. Light
  theme, white background, ink `#0F172A`, electric blue `#0052FF` accents,
  glass cards and dot-grid backgrounds (the design language of the earlier
  ONION LAB project).
* **Backend:** `vision-api/` (FastAPI on **8788**) — YOLOv8n single-class
  detector + TensorFlow verifier gate + fused condition ensemble
  (PyTorch CNN + sklearn RF + HSV heuristic behind a logistic meta-learner).
  See `vision-api/README.md` and `vision-api/METRICS.md` for measured numbers
  and their scope.

## One page

`Navbar → Hero (3D onion hero + spinning rings + floating sensor cards) →
Project story → How it works (4 steps) → Vision Lab (scanner) → 3D Explorer →
Metrics dashboard → Footer`

* **Vision Lab (scanner)** — the only screen a user needs: upload, live
  camera (permission requested **only on click**) or the bundled sample tray
  photo. While the camera is merely pointing, an **on-device colour heuristic**
  (F3) samples ~1 frame / 1.2 s on a 320 px canvas and draws live boxes —
  `FRESH-LOOKING COLORS` / `SUSPECT DARK AREAS` / `STRONG DARK/SPORE COLORS`
  with dark %, mould-colour % and sprout %, plus a per-onion variety estimate.
  It is clearly labelled *“colour heuristic — not the AI model; capture for
  the full verdict”*. Frames stay in memory.
* **Results** — GREEN `NO OBVIOUS VISIBLE DAMAGE` / YELLOW `NEEDS REVIEW` /
  RED `VISIBLE DAMAGE` with human sentences, findings from the 5-item
  vocabulary only, variety chips marked **est.**, tracking circles on the
  photo, and a model-signal “why was this flagged?” panel.
* **3D Explorer (deep analysis)** — the photographed side of each onion is
  texture-mapped onto a procedural 3D onion; suspected regions appear as
  pulsing **AI-INFERRED REGION** markers with the honesty caption (only the
  photographed side is real evidence). Layer-by-layer analysis (L1 measured /
  L2–L3 not visible / L4 not captured) and a full model-signal trace.
* **Metrics dashboard** — live values from `GET /api/health` (detector,
  verifier, condition, colour-shift table), every number carrying its scope.
* **PDF report** — a formal, black-on-white “ONION QUALITY INSPECTION REPORT”
  with report number, inspector lines, specimen photograph, per-onion
  observations table and **ANNEXURE A** (full limitations). No AI styling.

## One contract

Everything the UI renders flows through `src/types/vision.ts` →
`OnionResult[]` (now including `variety` + `varietyConfidence`). Engines are
swappable in `src/services/visionService.ts`:

* `VITE_VISION_API` (default `/vision-api`, proxied by Vite to `localhost:8788`)
  → **REMOTE INFERENCE API** (badge: LIVE).
* If the API is unreachable → graceful fallback to the in-browser HSV heuristic
  (**LOCAL DEMO**, amber badge — never a silent fake).

## Run

```bash
npm install
npm run dev            # http://localhost:5174
# plus the API:
cd vision-api && pip install -r requirements.txt
python3 -m uvicorn app:app --host 0.0.0.0 --port 8788
```

`.env.local` sets `VITE_VISION_API=/vision-api` (an `.env.example` documents
it; the app works without it by using the same default). A production build
(`VITE_VISION_API= npm run build`) is served directly by FastAPI when the
`dist/` folder is placed inside `vision-api/` (see the root `Dockerfile`).

## Browser e2e

```bash
node e2e/onion.e2e.mjs
```

Uploads the real 52-onion tray photo through the UI (expects results + engine
`REMOTE INFERENCE API` + zero page errors), downloads the PDF report, then
uploads a distractor image (expects 0 detections). The sandbox has no
Playwright CDN access, so the script drives the `@sparticuz/chromium` binary
(extract its bundled `al2023.tar.br` with brotli to `/tmp/al2023-libs` and set
`LD_LIBRARY_PATH=/tmp/al2023-libs/lib` when the platform lacks those libs).

## Honesty rules (enforced in UI + API)

* Camera permission is requested **only on click**; frames are processed
  in-memory and never stored or uploaded beyond the single analysis call.
* DEMO/LIVE badges are truthful: LIVE = remote inference engine answered;
  DEMO = local fallback heuristic.
* Status vocabulary: GREEN `NO OBVIOUS VISIBLE DAMAGE` · YELLOW `NEEDS REVIEW`
  · RED `VISIBLE DAMAGE`. Findings limited to: Surface Discoloration / Surface
  Damage / Possible Mold-Like Growth / Shriveling / Sprouting.
* Confidence values are **visual prediction confidence**, not food-safety
  probabilities. Variety labels are colour **estimates**, never ground truth.
* A camera cannot see inside an onion — internal quality is declared
  undeterminable on every screen and in the report (Annexure A).
