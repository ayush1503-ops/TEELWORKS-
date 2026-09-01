# 🚀 Deployment Guide (Phase 14) — click-by-click, free

**Recommended path: Render.com (free, ~10 minutes, no server admin).**
Alternatives below. All of them give you an **HTTPS URL** — important because
phone browsers only allow the live camera (`getUserMedia`) on secure pages
(this app also has a native-camera fallback, so it works either way).

---

## What gets deployed

The **whole repo** (not just `backend/`), because the app reads
`config/grading_rules.yaml` from the project root and serves `frontend/`:

```
onion-grader/
├── backend/       FastAPI app + requirements.txt
├── frontend/      the web UI (served by the same process)
├── config/        grading_rules.yaml  ← must be included!
└── scripts/       dataset/training (not needed at runtime, harmless)
```

**Verified start command** (tested):
```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## OPTION A — Render.com (recommended, free)

### Step 1 — Put the code on GitHub (5 min)

1. Create a free account at **github.com** (if you don't have one).
2. Click **+ → New repository** → name it `onion-quality-analyzer` → **Private** is fine → **Create**.
3. On your computer, in a terminal (Git Bash on Windows):

```bash
cd onion-grader
git init
git add .
git commit -m "Onion Quality Analyzer - full prototype"
git branch -M main
git remote add origin https://github.com/<your-username>/onion-quality-analyzer.git
git push -u origin main
```

(Install Git from git-scm.com first if needed. Windows: run these in *Git Bash*,
or upload the folder via GitHub's web interface — "uploading an existing file".)

### Step 2 — Create the service on Render (5 min)

1. Go to **render.com** → sign up **with GitHub** (connects your repos).
2. Dashboard → **New +** → **Web Service**.
3. Select your `onion-quality-analyzer` repo.
4. Fill in exactly:

| Field | Value |
|---|---|
| Name | `onion-quality-analyzer` |
| Region | Singapore (closest to India) |
| Branch | `main` |
| Runtime | **Python 3** |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | **Free** |

5. Click **Create Web Service** and watch the build log.
   First build takes ~3–5 min (installing OpenCV etc.).

### Step 3 — Use it

Your app is live at **`https://onion-quality-analyzer.onrender.com`**
(open on your phone → Take Photo works — it's HTTPS).

* API docs: `/docs` · Health: `/api/health`
* Auto-redeploys whenever you `git push` a change.

**Free-tier gotchas (know before the demo):**
* Sleeps after ~15 min idle → first visitor waits ~30–60 s (cold start).
  Fix: 30 min before presenting, open the URL once; or ping it with a free
  cron (cron-job.org → hit `/api/health` every 10 min).
* **SQLite is wiped on every redeploy** (ephemeral disk). Fine for the demo —
  analyses are also returned live in the API/UI. For persistence, move to
  Supabase Postgres (below).

**Deploying WITH the trained model:** `models/classifier.pkl` is git-ignored (binary artifact). Either (a) commit it once (`git add -f models/classifier.pkl`), or (b) regenerate it during the build — change the Render **Build Command** to:

```
pip install -r backend/requirements.txt && python scripts/generate_synthetic_dataset.py --out datasets/synthetic_v1 --per-class 90 --size 384 && python scripts/train_baseline.py --dataset datasets/synthetic_v1 --label synthetic-v1
```

Without it the app still runs honestly in rules-only mode (`model.trained_ml_loaded: false`).

---

## OPTION B — Hugging Face Spaces (free, Docker)

1. huggingface.co → **New Space** → SDK = **Docker** → Blank template.
2. Add this `Dockerfile` at the **repo root** (HF expects port 7860):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY . .
CMD ["sh", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
```

3. Upload the project files (web UI or `git push`).
4. Space URL: `https://<your-name>-<space-name>.hf.space`

## OPTION C — Railway / Koyeb / Fly.io (free trials)

Same idea: connect the GitHub repo →
Build `pip install -r backend/requirements.txt` →
Start `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
Railway/Koyeb auto-detect the `Dockerfile` too (use the `$PORT` version below).

**Generic Dockerfile (Render/Railway/Koyeb/Fly — reads $PORT):**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

## OPTION D — quick public URL for a demo (no hosting)

From your own laptop (project already running on localhost:8000):

```bash
# ngrok (free account)
ngrok http 8000
# or cloudflared (no account)
npx cloudflared tunnel --url http://localhost:8000
```

You get a temporary HTTPS URL — perfect for a 30-minute demo, nothing deployed.

## OPTION E — college VM / own server

```bash
git clone <your-repo> && cd onion-quality-analyzer
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Put nginx in front for HTTPS (certbot/Let's Encrypt) — needed for phone camera.

---

## After deploying: production hardening checklist

- [ ] HTTPS: automatic on all options above (required for live camera)
- [ ] Set CORS to your real domain: in `backend/app/main.py` replace
      `allow_origins=["*"]` with `["https://onion-quality-analyzer.onrender.com"]`
- [ ] Swap the in-memory rate limiter for a shared one (`slowapi`) if you run
      more than one instance
- [ ] Durability: move SQLite → **Supabase** free Postgres (same schema in
      `app/services/database.py`, connect via SQLAlchemy)
- [ ] When the official grading standard arrives: update
      `config/grading_rules.yaml`, set `official_standard: true`, bump
      `rule_version`, push — Render redeploys automatically

## SIH demo-day checklist

1. Open the deployed URL on a phone (or this workspace preview) — live camera works
2. Single onion: photo → annotated image → score breakdown → grade → PDF
3. **The accuracy moment:** Test tab → "🏁 Run held-out test set (live)" → judges watch
   105 unseen images classified — 100% with a perfect confusion-matrix diagonal,
   computed in front of them. Say exactly: *"100% measured on our 154-image
   held-out synthetic test set through the identical production pipeline; field
   validation is the next step."* That phrasing is bulletproof.
4. **Configurability proof:** edit `config/grading_rules.yaml` thresholds →
   push → re-analyse the same photo → grade changes
5. Batch tab: upload several photos → Grade A/B/C/URS % dashboard + batch PDF
6. Point at the disclaimers (internal quality, prototype rules, px vs mm) —
   judges reward honesty about limits
