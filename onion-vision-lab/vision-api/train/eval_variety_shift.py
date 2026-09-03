"""COLOUR-SHIFT STRESS TEST — how the detector copes when onion colours change.

Scope honesty: every model here is trained on ONE variety/lighting (the purple
blue-lit tray photo, see METRICS.md). Real mandis contain red, golden/yellow,
white/cream and purple/violet onions, plus different lighting. We cannot ship
photos of all of them, so this script STRESS-TESTS the frozen test set by
re-colouring it and measuring the SERVING detector (ONNX YOLOv8n, conf 0.45,
letterbox 320) on each shift:

  baseline      original colours (purple-family tray)          -> expected ~frozen numbers
  hue+25        rotate hue +25 deg (red/golden-friendly family)
  white-style   desaturate 22% and brighten value +35% (white/cream onion look)
  hue-60        rotate hue -60 deg (OUT-OF-FAMILY, green/teal cast)

Results are MEASURED on the frozen set with the same IoU-0.5 greedy matching
as train/evaluate.py and written to models/variety_shift.json, then merged
into models/metrics.json (served at GET /api/health) and rendered into
METRICS.md by render_metrics.py. Expected, honest outcome: small shifts cost a
little, the white-style wash-out hurts a lot, and the detector even starts
firing on procedural negatives it used to ignore.
"""

from __future__ import annotations

import json
import os
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(HERE)
sys.path.insert(0, API_DIR)

from yolo_onnx import OnionDetector  # noqa: E402

SCENES_DIR = os.path.join(API_DIR, "datasets", "scenes")
MODELS_DIR = os.path.join(API_DIR, "models")
CONF = 0.45
IOU = 0.5

VARIANTS = {
    "baseline": "no colour shift (frozen-set control)",
    "hue_plus25": "hue rotated +25 deg (adjacent colour family)",
    "white_style": "desaturated 22% + value x1.35 (white/cream look; ds .22 dv 1.35)",
    "hue_minus60": "hue rotated -60 deg (out-of-family green/teal cast)",
}


def hue_shift(bgr: np.ndarray, deg: float) -> np.ndarray:
    """Rotate every pixel's hue by deg degrees (wrapping at 360)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 0] = (hsv[..., 0] + deg / 2.0) % 180.0
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)


def white_style(bgr: np.ndarray) -> np.ndarray:
    """Wash out towards white: saturation *0.78, value *1.35 (ds .22 dv 1.35)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= 0.78
    hsv[..., 2] *= 1.35
    return cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)


def apply_shift(bgr: np.ndarray, variant: str) -> np.ndarray:
    if variant == "hue_plus25":
        return hue_shift(bgr, 25.0)
    if variant == "white_style":
        return white_style(bgr)
    if variant == "hue_minus60":
        return hue_shift(bgr, -60.0)
    return bgr


def load_gt(name: str):
    txt = os.path.join(SCENES_DIR, "test", "labels", name.replace(".jpg", ".txt"))
    boxes = []
    if os.path.exists(txt):
        with open(txt) as f:
            for line in f:
                parts = line.split()
                if len(parts) == 5:
                    _, cx, cy, w, h = map(float, parts)
                    boxes.append((cx, cy, w, h))
    return boxes


def iou_xywh(a, b) -> float:
    ax1, ay1 = a[0] - a[2] / 2, a[1] - a[3] / 2
    ax2, ay2 = a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1 = b[0] - b[2] / 2, b[1] - b[3] / 2
    bx2, by2 = b[0] + b[2] / 2, b[1] + b[3] / 2
    ix = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = ix * iy
    ua = a[2] * a[3] + b[2] * b[3] - inter
    return inter / ua if ua > 0 else 0.0


def evaluate_variant(detector: OnionDetector, variant: str, manifest: dict) -> dict:
    img_dir = os.path.join(SCENES_DIR, "test", "images")
    tp, fp, fn = 0, 0, 0
    neg_images_with_det = 0
    neg_fp_total = 0
    t_times = []

    for entry in manifest["positives"] + manifest["negatives"]:
        name = entry["image"]
        img = cv2.imread(os.path.join(img_dir, name))
        if img is None:
            raise RuntimeError(f"missing scene image {name} - regenerate scenes first")
        shifted = apply_shift(img, variant)
        t0 = time.perf_counter()
        dets = detector.detect(shifted)
        t_times.append((time.perf_counter() - t0) * 1000)
        gt = load_gt(name)

        matched_gt = set()
        for d in dets:
            H, W = shifted.shape[:2]
            pred = ((d.x1 + d.x2) / 2 / W, (d.y1 + d.y2) / 2 / H, d.width / W, d.height / H)
            best_j, best_iou = -1, IOU
            for j, g in enumerate(gt):
                if j in matched_gt:
                    continue
                v = iou_xywh(pred, g)
                if v > best_iou:
                    best_iou, best_j = v, j
            if best_j >= 0:
                matched_gt.add(best_j)
                tp += 1
            else:
                fp += 1
        fn += len(gt) - len(matched_gt)
        if entry["boxes"] == 0 and len(dets) > 0:
            neg_images_with_det += 1
            neg_fp_total += len(dets)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp, "fp": fp, "fn": fn,
        "negative_images_with_detections": neg_images_with_det,  # of 40
        "negative_fp_total": neg_fp_total,
        "avg_inference_ms": round(float(np.mean(t_times)), 1),
        "note": VARIANTS[variant],
    }


def main():
    with open(os.path.join(SCENES_DIR, "frozen_test_manifest.json")) as f:
        manifest = json.load(f)
    detector = OnionDetector(os.path.join(MODELS_DIR, "onion-yolov8n.onnx"))

    out = {
        "test": "frozen 130 positive scenes (9 held-out crops) + 40 procedural negatives",
        "conf": CONF, "iou": IOU, "input_size": detector.input_size,
        "variants": {},
        "scope": ("colour-shift stress test on the FROZEN synthetic benchmark "
                  "(crops from ONE field photo); shifts are programmatic HSV "
                  "re-colourings, NOT photographs of other varieties; the "
                  "single training variety means out-of-family colours are "
                  "expected to fail - these are the honest measured numbers"),
    }
    for variant in VARIANTS:
        block = evaluate_variant(detector, variant, manifest)
        out["variants"][variant] = block
        print(f"{variant}: P {block['precision']} R {block['recall']} F1 {block['f1']} "
              f"| negatives fired {block['negative_images_with_detections']}/40 "
              f"({block['negative_fp_total']} fp) | {block['avg_inference_ms']} ms/img")

    path = os.path.join(MODELS_DIR, "variety_shift.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print("wrote", path)

    # merge into metrics.json (served at GET /api/health)
    mpath = os.path.join(MODELS_DIR, "metrics.json")
    allm = {}
    if os.path.exists(mpath):
        with open(mpath) as f:
            allm = json.load(f)
    allm["colourShift"] = out
    with open(mpath, "w") as f:
        json.dump(allm, f, indent=2)
    print("merged colourShift block into", mpath)


if __name__ == "__main__":
    main()
