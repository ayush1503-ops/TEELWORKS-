"""Onion Vision Lab - FastAPI backend (Phase 2).

POST /api/analyze  {imageBase64, sourceMode}  ->  OnionResult[]
GET  /api/health   -> ensemble status + honest measured metrics

Pipeline: YOLOv8n single-class 'onion' (ONNX, conf 0.45, letterbox 320)
   -> TensorFlow/Keras onion-vs-not-onion verifier gate (ONNX serve)
   -> fused condition ensemble (PyTorch CNN + sklearn RF + HSV heuristic,
      logistic meta-learner) -> OnionResult[]

Frames are decoded in memory for the analyze call only - never stored.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from typing import List

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from schemas import AnalyzeRequest, AnalyzeResponse, OnionResult, Finding, RegionPoint, BBox, OnionMetrics
from yolo_onnx import OnionDetector, crop_detection
from ensemble import ConditionEnsemble, OnionVerifier, ENSEMBLE_VERSION, CONDITION_CLASSES

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
METRICS_PATH = os.path.join(MODELS_DIR, "metrics.json")
MAX_SIDE = 2200
MAX_DETECTIONS = 64

DISCLAIMERS = [
    "Analysis is limited to the VISIBLE surface captured in this image.",
    "Internal quality cannot be determined by any camera - no claim is made about the inside of the onion.",
    "Confidence values are the model's visual prediction confidence only, not a probability that the onion is safe or unsafe to eat.",
    "Findings are limited to: Surface Discoloration, Surface Damage, Possible Mold-Like Growth, Shriveling, Sprouting.",
    "Condition labels were trained on programmatic synthetic damage over real onion crops (see METRICS.md); field validation pending.",
]

app = FastAPI(title="Onion Vision Lab API", version="2.0.0-phase2")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_state = {"detector": None, "ensemble": None, "verifier": None, "verifier_tau": 0.5}


def _load_metrics() -> dict:
    try:
        with open(METRICS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def get_detector() -> OnionDetector:
    if _state["detector"] is None:
        path = os.path.join(MODELS_DIR, "onion-yolov8n.onnx")
        if not os.path.exists(path):
            raise HTTPException(status_code=503, detail="detector model missing: onion-yolov8n.onnx")
        _state["detector"] = OnionDetector(path)
    return _state["detector"]


def get_ensemble() -> ConditionEnsemble:
    if _state["ensemble"] is None:
        _state["ensemble"] = ConditionEnsemble(MODELS_DIR)
    return _state["ensemble"]


def get_verifier() -> OnionVerifier:
    if _state["verifier"] is None:
        metrics = _load_metrics()
        ver = metrics.get("phase2", {}).get("verifier", {})
        # serving gate tau is calibrated on VAL detections (see METRICS.md);
        # fall back to the binary-model tau if the calibration entry is absent
        tau = float(ver.get("serving_gate_threshold", ver.get("gate_threshold", 0.5)))
        _state["verifier"] = OnionVerifier(MODELS_DIR, threshold=tau)
        _state["verifier_tau"] = tau
    return _state["verifier"]


def decode_image(image_base64: str) -> np.ndarray:
    try:
        if "," in image_base64[:64] and image_base64.strip().startswith("data:"):
            image_base64 = image_base64.split(",", 1)[1]
        raw = base64.b64decode(image_base64, validate=False)
        if len(raw) > 12_000_000:
            raise HTTPException(status_code=413, detail="image too large")
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("undecodable")
        h, w = img.shape[:2]
        if max(h, w) > MAX_SIDE:
            scale = MAX_SIDE / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return img
    except HTTPException:
        raise
    except (binascii.Error, ValueError, Exception) as e:
        raise HTTPException(status_code=400, detail=f"invalid image payload: {e}")


def _engine_strings(det_ver: str, ens: ConditionEnsemble, ver: OnionVerifier) -> tuple:
    parts = ["YOLOv8n single-class 'onion' (ONNX)"]
    if ver.available:
        parts.append("TF/Keras onion verifier gate")
    if ens.available["cnn"]:
        parts.append("PyTorch MobileNetV3-Small condition CNN")
    if ens.available["rf"]:
        parts.append("sklearn RandomForest (calibrated)")
    parts.append("HSV heuristic + logistic meta-fusion" if ens.available["meta"] else "HSV heuristic (fallback fusion)")
    detail = " + ".join(parts)
    return "REMOTE INFERENCE API", detail


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    t0 = time.perf_counter()
    img = decode_image(req.imageBase64)
    h, w = img.shape[:2]

    detector = get_detector()
    t_det = time.perf_counter()
    dets = detector.detect(img)[:MAX_DETECTIONS]
    detect_ms = (time.perf_counter() - t_det) * 1000

    ensemble = get_ensemble()
    verifier = get_verifier()

    t_cond = time.perf_counter()
    results: List[OnionResult] = []
    dropped_by_verifier = 0
    kept = 0
    for i, det in enumerate(dets):
        crop = crop_detection(img, det, pad=0.08)
        if crop.size == 0:
            continue
        verdict, p_onion = None, None
        if verifier.available:
            verdict, p_onion = verifier.is_onion(crop)
            if verdict is False:
                dropped_by_verifier += 1
                continue
        cond = ensemble.predict(crop)
        kept += 1
        findings = [Finding(kind=f["kind"], confidence=round(float(f["confidence"]), 3), evidence=f["evidence"])
                    for f in cond["findings"]]
        results.append(OnionResult(
            id=f"onion-{kept}",
            bbox=BBox(x=det.x1 / w, y=det.y1 / h, width=det.width / w, height=det.height / h),
            status=cond["statusColor"],
            statusLabel=cond["statusLabel"],
            confidence=round(float(min(0.99, det.conf * (0.35 + 0.65 * cond["confidence"]))), 3),
            findings=findings,
            regions=[RegionPoint(**r) for r in cond["regions"]],
            metrics=OnionMetrics(
                darkRatio=round(cond["cues"]["darkRatio"], 4),
                saturationStd=round(cond["cues"]["satStd"], 2),
                greenTop=round(cond["cues"]["greenTop"], 4),
                detectorConfidence=round(det.conf, 3),
                verifierConfidence=None if p_onion is None else round(p_onion, 3),
            ),
            modelName=f"onion-yolov8n + {ENSEMBLE_VERSION}",
            notes=cond["fusion"],
            signals={k: v for k, v in cond["signals"].items()},
        ))
    cond_ms = (time.perf_counter() - t_cond) * 1000

    engine, detail = _engine_strings("2", ensemble, verifier)
    return AnalyzeResponse(
        engine=engine,
        engineDetail=detail,
        imageWidth=w,
        imageHeight=h,
        results=results,
        meta={
            "sourceMode": req.sourceMode,
            "detectedRaw": len(dets),
            "verifierDropped": dropped_by_verifier,
            "kept": kept,
            "timingsMs": {"detect": round(detect_ms, 1), "condition+verify": round(cond_ms, 1),
                          "total": round((time.perf_counter() - t0) * 1000, 1)},
            "ensembleAvailable": ensemble.available,
            "fusion": results[0].notes if results else "n/a",
            "disclaimers": DISCLAIMERS,
        },
    )


@app.get("/api/health")
def health():
    metrics = _load_metrics()
    detector_ok = os.path.exists(os.path.join(MODELS_DIR, "onion-yolov8n.onnx"))
    ensemble = get_ensemble()
    verifier = get_verifier()
    det_block = metrics.get("detection", {})
    ph2 = metrics.get("phase2", {})
    return {
        "status": "ok" if detector_ok else "degraded",
        "service": "onion-vision-lab/vision-api",
        "version": "2.0.0-phase2",
        "engine": "REMOTE INFERENCE API",
        "pipeline": {
            "detector": {
                "loaded": detector_ok,
                "architecture": "YOLOv8n, single class 'onion', ONNX",
                "conf": 0.45, "inputSize": 320,
                "measured": {k: det_block.get(k) for k in ("precision", "recall", "f1", "map50", "scope")},
            },
            "verifier": {
                "loaded": verifier.available,
                "architecture": "TensorFlow/Keras CNN (binary onion vs not-onion), served via ONNX",
                "gateThreshold": _state["verifier_tau"],
                "measured": ph2.get("verifier", {}),
                "gateMeasured": ph2.get("verifier_gate", {}),
            },
            "condition": {
                "architecture": "PyTorch MobileNetV3-Small CNN + sklearn calibrated RF + HSV heuristic, logistic meta-fusion",
                "available": ensemble.available,
                "version": ENSEMBLE_VERSION,
                "measured": ph2.get("condition", {}),
            },
        },
        "metricsSource": "models/metrics.json (see METRICS.md for full tables + scopes)",
        "disclaimers": DISCLAIMERS,
    }


# ---------------------------------------------------------------------------
# Static frontend serving (production / single-container deployment)
# Mount AFTER all API routes so /api/... always hits the routes above.
# Guarded: only activated when the Vite dist/ folder is present (i.e. the
# Docker multi-stage build has placed it here). In dev the folder is absent
# and the API runs stand-alone with Vite's dev server proxying /vision-api.
# ---------------------------------------------------------------------------
_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.isdir(_DIST_DIR):
    app.mount("/", StaticFiles(directory=_DIST_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8788)
