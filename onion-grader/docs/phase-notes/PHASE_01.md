# Phase 1 — Image Input Interface (Beginner Walkthrough)

**Status: ✅ complete.** This document explains what was built, why, how to run
it, how to test it, and what usually goes wrong.

---

## 1. What we built

A mobile-friendly web interface and a minimal FastAPI backend that together
implement the first step of the workflow:

```
HOME → TAKE PHOTO / UPLOAD → IMAGE PREVIEW → ANALYZE → PROCESSING → RESULT
```

In Phase 1, **Analyze** sends the image to `POST /api/analyze`, which validates
it and returns *real measured facts* (format, dimensions, file size). It does
**not** return any score, grade or defect — the AI pipeline arrives in Phase 2.
The app says this openly instead of inventing results.

## 2. Why we need it

* Procurement-centre staff need the simplest possible start: two big buttons.
* Every later phase (detection, scoring, grading, reports) hangs off this exact
  screen + API contract — we are building the skeleton first.
* Security habits (file validation, size limits, rate limiting) are cheapest to
  install on day one.

## 3. Folder structure (only the Phase 1 files)

```
onion-grader/
├── README.md                     overview + quickstart
├── docs/
│   ├── ARCHITECTURE.md           full system design
│   ├── PHASES.md                 roadmap tracker
│   └── phase-notes/PHASE_01.md   this file
├── backend/
│   ├── requirements.txt          Python dependencies
│   ├── run.py                    `python run.py` launcher
│   ├── app/
│   │   ├── main.py               FastAPI app: API routes + serves frontend
│   │   ├── api/health.py         GET /api/health
│   │   ├── api/analyze.py        POST /api/analyze (honest stub)
│   │   ├── core/config.py        limits, paths, metadata
│   │   ├── core/security.py      validation + rate limiter  ← the security core
│   │   └── schemas/analyze.py    response models (the API contract)
│   └── tests/test_api.py         8 automated tests
└── frontend/
    ├── index.html                the four screens
    ├── css/style.css             mobile-first styling
    └── js/app.js                 view switching, camera, upload, analyze
```

## 4. Installation

```bash
cd onion-grader/backend
python3 -m pip install -r requirements.txt
```

(On your own machine later, first create a virtual environment:
`python3 -m venv .venv` → `source .venv/bin/activate` on macOS/Linux or
`.venv\Scripts\activate` on Windows, then run the pip command above.)

## 5. Code — what each piece does

| File | Responsibility | Key idea |
|---|---|---|
| `app/main.py` | Creates the FastAPI app, mounts `/api/*` routes, then serves `frontend/` as static files | One service = API + UI → no CORS pain, simple deploy |
| `app/api/analyze.py` | The endpoint the app calls | Rate-limit → validate → return an *honest* stub response |
| `app/core/security.py` | 4-step upload validation + sliding-window rate limiter | Extension → size → **magic bytes** → full Pillow decode; in-memory only, never written to disk |
| `app/schemas/analyze.py` | Pydantic models | Fixes the JSON contract so later phases only *add* fields |
| `frontend/js/app.js` | Screen flow + camera | `getUserMedia` live camera with automatic fallback to `<input capture>` (native camera) when blocked |
| `frontend/index.html` + `css/style.css` | The 4 screens (home / preview / processing / result), large buttons | Mobile-first, warm palette, works on a phone browser |

## 6. How to run it

```bash
cd onion-grader/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
# or: python run.py
```

Open http://localhost:8000 (phone: same Wi-Fi, `http://<your-ip>:8000`).
Auto-generated API docs: http://localhost:8000/docs

## 7. Expected output

**In the browser** — Home with two big buttons → take/upload a photo → preview
with Retake/Analyze → brief spinner → result card:

> ✓ Image validated & received
> `JPEG` `3000×4000 px` `12.0 MP` `2415 KB`
> ⚠ **AI analysis is not connected yet.** Image received and validated
> successfully… (honest message)
> What comes next: Phase 2 — OpenCV…, Phase 3 — …, etc.

**From the API** (curl example):

```bash
curl -F "file=@onion.jpg" http://localhost:8000/api/analyze
```

```json
{
  "status": "image_validated",
  "analysis_available": false,
  "message": "Image received and validated successfully. The AI analysis pipeline is not connected yet...",
  "image": {
    "filename": "onion.jpg", "format": "JPEG",
    "width": 3000, "height": 4000,
    "size_bytes": 2415000, "megapixels": 12.0, "aspect_ratio": 0.75
  },
  "next_steps": ["Phase 2 — OpenCV preprocessing + onion detection...", "..."],
  "phase": 1,
  "app_version": "0.1.0"
}
```

## 8. How to test it

**Automated** (8 tests):

```bash
cd onion-grader/backend && pytest -v
```

Covers: health check · real JPEG accepted with true metadata · real PNG ·
`analysis_available` must be false (anti-fake-AI test!) · fake `.jpg` (text)
rejected 415 · `.gif` rejected 415 · empty file 400 · oversized 413 · rate
limit 429.

**Manual security probes:**

```bash
printf 'definitely not an image' > /tmp/fake.jpg
curl -i -F "file=@/tmp/fake.jpg" http://localhost:8000/api/analyze   # → 415
curl -i -F "file=@notes.txt"      http://localhost:8000/api/analyze  # → 415
```

**Manual UI checks:** upload a JPG (< 8 MB) → result card appears · upload a
15 MB image → friendly error · press Take Photo → live camera (or native
camera on phone) · Analyze with server stopped → error banner.

## 9. Common errors and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: app` | Running uvicorn from the wrong folder | `cd backend` first, then run uvicorn |
| `Form data requires "python-multipart"` | Missing upload dependency | `pip install python-multipart` (it's in requirements.txt) |
| `Address already in use` port 8000 | Another server on that port | `uvicorn ... --port 8001` |
| Live camera doesn't open in an embedded preview | Browser blocks `getUserMedia` inside some iframes | The app auto-falls back to the native camera input; or open the page URL directly in a new tab / on your phone |
| `413` on upload | Image > 8 MB | Re-take photo or compress; limit is in `core/config.py` |
| `415` on upload | Not a real JPG/PNG (or wrong extension) | Use a real photo; only JPG/JPEG/PNG |
| `429` | Rate limit hit (20 req/min/IP) | Wait a minute (test-friendly default; tunable in config) |
| Page loads but buttons do nothing | JavaScript error | Open browser DevTools console (F12) and check for errors |

## 10. What Phase 2 will change (preview)

`app/api/analyze.py` will call the new OpenCV service
(`app/services/preprocessing.py`) and return real detections, measurements and
an annotated image — the frontend will display them without structural changes.
