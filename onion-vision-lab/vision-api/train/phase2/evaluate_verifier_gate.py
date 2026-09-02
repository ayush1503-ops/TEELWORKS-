"""Detection-level gate evaluation: verifier ON vs OFF on the FROZEN test set.

tau selection (honest, on VAL detections only):
  1. run the detector on VAL positive scenes, greedy-match predictions to GT
     at IoU 0.5, collect p_onion for TRUE-positive crops
  2. tau = min(0.5, 1st-percentile of TP p_onion)  -> gate keeps >=99% of TPs
  3. evaluate the frozen TEST with that tau (before/after)
Reports FP before/after on the 40 frozen negatives, recall change, and the
detection count kept on the real 52-onion demo photo. Writes metrics.json.
"""

from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, API_DIR)
sys.path.insert(0, os.path.join(API_DIR, "train"))

MODELS_DIR = os.path.join(API_DIR, "models")
SCENES_DIR = os.path.join(API_DIR, "datasets", "scenes")
DEMO_PHOTO = os.path.join(API_DIR, "..", "scan_demo_52_onions.jpg")


def collect_val_tp_scores(detector, verifier) -> np.ndarray:
    """p_onion scores of TRUE-positive detection crops on the VAL positives."""
    img_dir = os.path.join(SCENES_DIR, "val", "images")
    lbl_dir = os.path.join(SCENES_DIR, "val", "labels")
    scores = []
    from yolo_onnx import crop_detection
    from evaluate import iou_xywh
    for f in sorted(os.listdir(img_dir)):
        lbl_path = os.path.join(lbl_dir, f.replace(".jpg", ".txt"))
        gt = []
        if os.path.exists(lbl_path):
            for line in open(lbl_path):
                p = line.split()
                if len(p) == 5:
                    gt.append(tuple(map(float, p[1:])))
        if not gt:
            continue
        img = cv2.imread(os.path.join(img_dir, f))
        H, W = img.shape[:2]
        matched = set()
        for d in detector.detect(img):
            pred = ((d.x1 + d.x2) / 2 / W, (d.y1 + d.y2) / 2 / H, d.width / W, d.height / H)
            best_j, best_iou = -1, 0.5
            for j, g in enumerate(gt):
                if j in matched:
                    continue
                v = iou_xywh(pred, g)
                if v > best_iou:
                    best_iou, best_j = v, j
            if best_j >= 0:
                matched.add(best_j)
                crop = crop_detection(img, d, pad=0.08)
                scores.append(verifier.p_onion(crop))
    return np.array(scores, dtype=np.float64)


def main():
    from yolo_onnx import OnionDetector, crop_detection
    from ensemble import OnionVerifier
    import evaluate as det_eval

    detector = OnionDetector(os.path.join(MODELS_DIR, "onion-yolov8n.onnx"))
    with open(os.path.join(MODELS_DIR, "phase2", "verifier.json")) as f:
        ver_metrics = json.load(f)

    # ---- tau selection on VAL detections (before touching TEST) ----
    tau_selector = OnionVerifier(MODELS_DIR, threshold=0.0)  # score reader
    tp_scores = collect_val_tp_scores(detector, tau_selector)
    assert len(tp_scores) > 50, f"too few val TPs: {len(tp_scores)}"
    tau = float(min(0.5, np.quantile(tp_scores, 0.01)))
    val_tp_kept = float((tp_scores >= tau).mean())
    print(f"tau selected on VAL: {tau:.4f} (keeps {val_tp_kept*100:.1f}% of {len(tp_scores)} TP crops)")

    verifier = OnionVerifier(MODELS_DIR, threshold=tau)
    assert verifier.available, "verifier.onnx missing - train it first"

    before = det_eval.evaluate(detector)
    after = det_eval.evaluate(detector, verifier=verifier)

    demo = cv2.imread(DEMO_PHOTO) if os.path.exists(DEMO_PHOTO) else cv2.imread(
        "/home/user/TEELWORKS-/onion-vision-lab/scan_demo_52_onions.jpg")
    dets_demo = detector.detect(demo)
    kept_demo = 0
    for d in dets_demo:
        crop = crop_detection(demo, d, pad=0.08)
        v, p = verifier.is_onion(crop)
        if v is not False:
            kept_demo += 1

    out = {
        "framework": "tensorflow (served via ONNX)",
        "gate_threshold": round(tau, 4),
        "tau_selection": ("min(0.5, 1st percentile of VAL true-positive p_onion scores); "
                          f"keeps {round(val_tp_kept, 4)} of {len(tp_scores)} val TPs"),
        "before": {k: before[k] for k in ("precision", "recall", "f1", "map50", "fp", "tp", "fn",
                                          "negative_images_with_detections", "negative_fp_total")},
        "after": {k: after[k] for k in ("precision", "recall", "f1", "map50", "fp", "tp", "fn",
                                        "negative_images_with_detections", "negative_fp_total")},
        "fp_removed_on_negatives": before["negative_fp_total"] - after["negative_fp_total"],
        "recall_delta": round(after["recall"] - before["recall"], 4),
        "demo_photo": {"raw_detections": len(dets_demo), "kept_after_gate": kept_demo,
                       "note": "real 52-onion tray photo (source of all crops)"},
        "scope": ("frozen test set (130 positive scenes from 9 held-out crops + 40 procedural "
                  "distractor negatives); gate = TF verifier at tau"),
    }
    mpath = os.path.join(MODELS_DIR, "metrics.json")
    allm = {}
    if os.path.exists(mpath):
        with open(mpath) as f:
            allm = json.load(f)
    allm.setdefault("phase2", {})
    allm["phase2"]["verifier_gate"] = out
    allm["phase2"]["verifier"] = {k: ver_metrics[k] for k in
                                  ("model", "params", "imgsz", "batch", "epochs",
                                   "test_binary_acc", "test_auc", "gate_threshold",
                                   "val_recall_at_tau", "val_fpr_at_tau",
                                   "test_confusion_at_tau", "data", "scope")}
    allm["phase2"]["verifier"]["serving_gate_threshold"] = round(tau, 4)
    with open(mpath, "w") as f:
        json.dump(allm, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
