"""Detection benchmark on the FROZEN test set (never modified).

Measures the SERVING stack exactly as /api/analyze uses it:
ONNX YOLOv8n, conf 0.45, letterbox 320 (train-matched). Greedy IoU-0.5
matching, then precision / recall / F1 / mAP50 (single class, 101-point
interpolation). Writes the `detection` block of models/metrics.json.
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


def evaluate(detector: OnionDetector, verifier=None) -> dict:
    with open(os.path.join(SCENES_DIR, "frozen_test_manifest.json")) as f:
        manifest = json.load(f)
    img_dir = os.path.join(SCENES_DIR, "test", "images")

    tp, fp, fn = 0, 0, 0
    scores, is_tp = [], []
    neg_images_with_det = 0
    neg_fp_total = 0
    per_image = []
    t_times = []

    for entry in manifest["positives"] + manifest["negatives"]:
        name = entry["image"]
        img = cv2.imread(os.path.join(img_dir, name))
        t0 = time.perf_counter()
        dets = detector.detect(img)
        t_times.append((time.perf_counter() - t0) * 1000)
        gt = load_gt(name)
        if verifier is not None:
            from yolo_onnx import crop_detection
            kept = []
            for d in dets:
                crop = crop_detection(img, d, pad=0.08)
                v, p = verifier.is_onion(crop)
                if v is not False:
                    kept.append(d)
            dets = kept

        matched_gt = set()
        img_tp = img_fp = 0
        for d in dets:
            H, W = img.shape[:2]
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
                img_tp += 1
                scores.append(d.conf)
                is_tp.append(1)
            else:
                img_fp += 1
                scores.append(d.conf)
                is_tp.append(0)
        fn += len(gt) - len(matched_gt)
        tp += img_tp
        fp += img_fp
        if entry["boxes"] == 0 and len(dets) > 0:
            neg_images_with_det += 1
            neg_fp_total += len(dets)
        per_image.append({"image": name, "gt": len(gt), "tp": img_tp, "fp": img_fp})

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    # AP50 (VOC-style, 101-point)
    order = np.argsort(scores)[::-1]
    tp_arr = np.array(is_tp, dtype=np.float64)[order]
    fp_arr = 1 - tp_arr
    ctp, cfp = np.cumsum(tp_arr), np.cumsum(fp_arr)
    rec = ctp / max(tp, 1)
    prec = ctp / np.maximum(ctp + cfp, 1e-9)
    mrec = np.concatenate([[0.0], rec, [1.0]])
    mpre = np.concatenate([[0.0], prec, [0.0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    grid = np.linspace(0, 1, 101)
    ap = float(np.mean(np.interp(grid, mrec, mpre)))

    return {
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f1": round(f1, 4), "map50": round(ap, 4),
        "tp": tp, "fp": fp, "fn": fn,
        "negative_images_with_detections": neg_images_with_det,
        "negative_fp_total": neg_fp_total,
        "avg_inference_ms": round(float(np.mean(t_times)), 1),
        "conf": CONF, "iou": IOU, "input_size": detector.input_size,
        "scope": ("frozen synthetic copy-paste benchmark from ONE field photo "
                  "(130 positive scenes from 9 held-out crops + 40 procedural "
                  "distractor-only negatives); field validation pending"),
    }


def main():
    detector = OnionDetector(os.path.join(MODELS_DIR, "onion-yolov8n.onnx"))
    metrics = evaluate(detector)
    print(json.dumps(metrics, indent=2))
    mpath = os.path.join(MODELS_DIR, "metrics.json")
    allm = {}
    if os.path.exists(mpath):
        with open(mpath) as f:
            allm = json.load(f)
    allm["detection"] = metrics
    with open(mpath, "w") as f:
        json.dump(allm, f, indent=2)
    print("metrics.json updated")


if __name__ == "__main__":
    main()
