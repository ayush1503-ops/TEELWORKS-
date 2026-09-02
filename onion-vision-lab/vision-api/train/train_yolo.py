"""Train the single-class YOLOv8n 'onion' detector (CPU-only, 2 vCPU budget).

Dataset: v2 (520 positive train scenes + 400 distractor hard negatives,
130 val scenes + 40 val negatives). Small imgsz + batch to fit the sandbox;
training is logged to a file (train_yolo.log) because pipes hide OOM kills.

15 epochs = the validated plateau of this configuration (from-scratch,
imgsz 320; earlier longer runs plateaued by epoch ~14-15 - see METRICS.md).
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import time

os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp")
os.environ.setdefault("OMP_NUM_THREADS", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(HERE)
SCENES_DIR = os.path.join(API_DIR, "datasets", "scenes")
MODELS_DIR = os.path.join(API_DIR, "models")
RUNS_DIR = os.path.join(API_DIR, "datasets", "runs")

EPOCHS = int(os.environ.get("YOLO_EPOCHS", "15"))
IMGSZ = int(os.environ.get("YOLO_IMGSZ", "320"))
BATCH = int(os.environ.get("YOLO_BATCH", "8"))


def main():
    from ultralytics import YOLO

    os.makedirs(MODELS_DIR, exist_ok=True)
    # NOTE: pretrained COCO weights (yolov8n.pt) are NOT reachable from this
    # sandbox (network restricted to PyPI/npm), so the detector is trained
    # FROM SCRATCH on the project dataset. Documented in METRICS.md.
    model = YOLO("yolov8n.yaml")
    t0 = time.time()
    results = model.train(
        data=os.path.join(SCENES_DIR, "dataset.yaml"),
        epochs=EPOCHS, imgsz=IMGSZ, batch=BATCH,
        device="cpu", workers=2, cache=False, seed=26031,
        project=RUNS_DIR, name="onion_v2", exist_ok=True,
        patience=30, plots=True, verbose=True,
        warmup_epochs=3, close_mosaic=10,
    )
    dt = time.time() - t0

    # ultralytics 8.4 nests runs under <project>/runs/<name> sometimes
    candidates = sorted(glob.glob(os.path.join(RUNS_DIR, "**", "onion_v2*", "**", "weights", "best.pt"),
                                  recursive=True)) + \
                 sorted(glob.glob(os.path.join(RUNS_DIR, "onion_v2*", "weights", "best.pt")))
    best = None
    for c in candidates:
        if os.path.exists(c):
            best = c
    assert best, f"best.pt not found under {RUNS_DIR}; searched {candidates}"
    print("best weights:", best)

    trained = YOLO(best)
    shutil.copy(best, os.path.join(MODELS_DIR, "onion-yolov8n.pt"))

    # Export dynamic-axis ONNX (serving letterbox is chosen on VAL - see
    # evaluate.py / METRICS.md; the model was trained at 320).
    onnx_path = trained.export(format="onnx", imgsz=IMGSZ, opset=12, dynamic=True, simplify=True)
    dest = os.path.join(MODELS_DIR, "onion-yolov8n.onnx")
    shutil.copy(onnx_path, dest)

    import csv
    rc = os.path.join(os.path.dirname(os.path.dirname(best)), "results.csv")
    epochs_done = None
    if os.path.exists(rc):
        with open(rc) as f:
            epochs_done = max(1, len(list(csv.reader(f))) - 1)

    summary = {
        "epochs": epochs_done or EPOCHS, "imgsz": IMGSZ, "batch": BATCH,
        "train_seconds": round(dt, 1),
        "best_weights_source": best,
        "onnx": dest,
        "note": "from-scratch training (COCO weights unreachable in sandbox); see METRICS.md",
        "results_dict": {k: (round(float(v), 4) if isinstance(v, (int, float)) else str(v))
                          for k, v in (getattr(results, "results_dict", {}) or {}).items()},
    }
    with open(os.path.join(MODELS_DIR, "train_yolo_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
