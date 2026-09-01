"""FastAPI entry point — full prototype (Phases 1–14).

    /api/health                 liveness + phase
    /api/analyze                one onion → features, defects, score, grade
    /api/batch                  many onions → Grade A/B/C/URS % + URS share
    /api/report/{id}.pdf        single-onion PDF report
    /api/report/batch/{id}.pdf  batch PDF report
    /api/analyses/recent        recent analyses (facts only)
    /api/evaluate[/metrics]     testing page: actual vs predicted + metrics
    /                           mobile-first web frontend
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import analyze, batch, evaluate, health, reports, scan
from app.core.config import APP_NAME, APP_VERSION, CURRENT_PHASE, FRONTEND_DIR

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "SIH 26031 prototype — objective onion quality assessment. "
        "Layers: A) OpenCV measurements, B) rule-based defect findings "
        "(ML slots in at Phase 5), C) transparent scoring, D) configurable "
        f"grading rules. Built through Phase {CURRENT_PHASE}."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(batch.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")
app.include_router(scan.router, prefix="/api")

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
