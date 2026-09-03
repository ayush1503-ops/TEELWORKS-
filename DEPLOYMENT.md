# Deploying Onion Vision Lab v2 on Render (Free Tier)

This guide walks you through deploying the complete Onion Vision Lab v2
(React frontend + FastAPI inference backend) as a **single Docker web service**
on Render's free tier — no persistent disk, no separate database.

---

## Architecture Overview

```
Browser
  │  GET /           → React SPA (served from FastAPI StaticFiles)
  │  POST /api/analyze
  └─ GET  /api/health
        │
     FastAPI (uvicorn, port $PORT)
        ├── /api/analyze  ← YOLOv8n + verifier + condition ensemble
        ├── /api/health   ← pipeline status + metrics
        └── /             ← Vite dist/ (StaticFiles, html=True)
```

The Docker image is built in two stages:
1. **Node 20 Alpine** — `npm ci` + `VITE_VISION_API= npm run build` → `dist/`
2. **Python 3.11 Slim** — pip installs, copies `dist/` into `vision-api/dist/`
   so FastAPI serves the SPA at `/`.

All model weights are **baked into the image** (no download at boot).

---

## Prerequisites

- A [Render](https://render.com) account (free tier is sufficient)
- This repository forked or pushed to GitHub (public or connected private repo)
- No environment variables required for basic deployment

---

## Step-by-Step Deployment

### 1. Fork / Push the Repository

Ensure the repository (including `Dockerfile` and `render.yaml` at the root) is
pushed to GitHub under your account or organisation.

```bash
git push origin arena/01a06535-teelworks
# then merge to main via the PR, or deploy directly from the branch
```

### 2. Connect Render to GitHub

1. Log in to [render.com](https://render.com)
2. Click **New +** → **Web Service**
3. Click **Connect a repository** and authorise Render to access your GitHub

### 3. Create the Web Service

**Option A — Using render.yaml (Blueprint)**

1. Click **New +** → **Blueprint**
2. Select your repository
3. Render detects `render.yaml` automatically and pre-fills:
   - **Runtime:** Docker
   - **Dockerfile path:** `./Dockerfile`
   - **Health check path:** `/api/health`
   - **Plan:** Free
4. Click **Apply** — Render triggers the first build

**Option B — Manual (no Blueprint)**

1. Click **New +** → **Web Service**
2. Select your repository
3. Fill in:
   | Field | Value |
   |---|---|
   | **Runtime** | Docker |
   | **Dockerfile path** | `./Dockerfile` (repo root) |
   | **Branch** | `main` (or your preferred branch) |
   | **Plan** | Free |
   | **Health Check Path** | `/api/health` |
4. Leave all env vars at their defaults (Render injects `PORT` automatically)
5. Click **Create Web Service**

### 4. Wait for the Build

The first build takes **5–10 minutes** (Node build + Python pip install +
~180 MB model weights baked in). You can watch the build log in the Render
dashboard.

When the build completes, Render shows **"Live"** and provides a URL like:
```
https://onion-vision-lab-xxxx.onrender.com
```

### 5. Verify the Deployment

```bash
# Health check — should return {"status": "ok", ...}
curl https://onion-vision-lab-xxxx.onrender.com/api/health

# Frontend — should return the React SPA HTML
curl -I https://onion-vision-lab-xxxx.onrender.com/
```

Or just open the URL in your browser and use the Upload or Camera mode.

---

## ⚠️ Free Tier Limitations

| Limitation | Detail |
|---|---|
| **Idle sleep** | Free instances spin down after **15 minutes of inactivity** |
| **Cold-start latency** | First request after sleep takes **30–60 seconds** (models re-load into RAM) |
| **RAM** | 512 MB — sufficient for all three models (YOLOv8n ONNX ~6 MB, verifier ONNX ~1.5 MB, condition CNN ONNX ~8 MB) |
| **CPU** | Shared — inference is CPU-only; expect ~50–200 ms per image (warmed) |
| **Disk** | No persistent disk required — models are in the Docker image |
| **Bandwidth** | 100 GB/month outbound (free tier) |
| **Build minutes** | 500 min/month free |

> **Tip:** You can use [UptimeRobot](https://uptimerobot.com) (free) to ping
> `/api/health` every 14 minutes and keep the instance warm. Note that Render
> may still enforce sleep on free-tier services regardless of external pings;
> upgrading to the Starter plan ($7/month) eliminates sleep entirely.

---

## Local Docker Test

If you have Docker installed locally:

```bash
# From the repo root
docker build -t onion-vision-lab .

# Run (maps host 8788 → container 8788)
docker run -p 8788:8788 onion-vision-lab

# Test
curl http://localhost:8788/api/health
open http://localhost:8788/
```

---

## Local Dev (no Docker)

```bash
# Terminal 1 — vision API
cd onion-vision-lab/vision-api
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8788 --reload

# Terminal 2 — frontend dev server (proxies /vision-api → localhost:8788)
cd onion-vision-lab
npm ci
npm run dev
# Open http://localhost:5174
```

---

## Updating the Deployment

Push a new commit to the connected branch. If `autoDeploy: true` is set in
`render.yaml` (or enabled in the Render dashboard), Render rebuilds and
redeploys automatically within a few minutes.

---

*See [LIMITATIONS.md](onion-vision-lab/LIMITATIONS.md) for an honest account
of model scope and known limitations before drawing conclusions from results.*
