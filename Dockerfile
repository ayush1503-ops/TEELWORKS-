# =============================================================================
# Onion Vision Lab v2 — Multi-stage Dockerfile
# =============================================================================
# Stage 1 (node:20-alpine): build the React/Vite frontend with VITE_VISION_API=''
#   so all API calls are relative (/api/...) and work same-origin in production.
# Stage 2 (python:3.11-slim): install vision-api deps, copy models + built
#   frontend into vision-api/dist, expose port 8788, run uvicorn.
#
# Render free tier:
#   - Set the PORT env var (Render injects it automatically).
#   - No persistent disk required — models are baked into the image.
#   - First request after a cold-start takes 30-60 s (model loading).
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — Node.js frontend build
# -----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /app

# Copy only the frontend source (not vision-api, not root Dockerfile)
COPY onion-vision-lab/package.json onion-vision-lab/package-lock.json ./

# Install dependencies (ci = exact lock-file install, no network for audits)
RUN npm ci --prefer-offline

# Copy the rest of the frontend source
COPY onion-vision-lab/ ./

# Build with VITE_VISION_API='' so the browser uses relative /api/... URLs
# (same-origin, no Vite proxy needed in production)
RUN VITE_VISION_API= npm run build

# Built output is in /app/dist

# -----------------------------------------------------------------------------
# Stage 2 — Python API image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS api

# System dependencies needed by opencv-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python serving dependencies first (layer-cached unless reqs change)
COPY onion-vision-lab/vision-api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the vision-api source (app.py, schemas.py, ensemble.py, etc.)
COPY onion-vision-lab/vision-api/ ./

# Copy pre-trained model weights (baked into the image; no download needed)
# Already included via the COPY above (models/ is under vision-api/)

# Copy the built frontend from Stage 1 into vision-api/dist so FastAPI's
# StaticFiles mount at "/" activates (guarded by os.path.isdir check in app.py)
COPY --from=frontend-build /app/dist ./dist

# Expose the default port (Render overrides via the PORT env var)
EXPOSE 8788

# Render sets $PORT; fall back to 8788 for local docker run
ENV PORT=8788

# Start uvicorn; $PORT is expanded by the shell
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8788}"]
