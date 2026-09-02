"""Export the best YOLO weights to models/ (dynamic-axis ONNX + .pt).

Used when training is stopped early (manual cut at a validated plateau) -
picks the latest best.pt from the ultralytics run tree (8.4 nests runs under
<project>/runs/<name>), evaluates it on the val split, copies the checkpoint
and exports ONNX with dynamic input size (serving letterbox is chosen on VAL).
"""

from __future__ import annotations

import csv
import glob
import json
import os
import shutil

os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp")

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(HERE)
RUNS_DIR = os.path.join(API_DIR, "datasets", "runs")
MODELS_DIR = os.path.join(API_DIR, "models")


def main():
    from ultralytics import YOLO

    cands = sorted(glob.glob(os.path.join(RUNS_DIR, "**", "onion_v2*", "**", "weights", "best.pt"), recursive=True)) + \
            sorted(glob.glob(os.path.join(RUNS_DIR, "onion_v2*", "weights", "best.pt")))
    cands = [c for c in cands if os.path.exists(c)]
    assert cands, "no best.pt found"
    best = max(cands, key=os.path.getmtime)
    print("best.pt:", best)

    model = YOLO(best)
    metrics = model.val(data=os.path.join(API_DIR, "datasets", "scenes", "dataset.yaml"),
                        imgsz=320, split="val", verbose=False, plots=False)
    mr = metrics.results_dict
    print("val:", {k: round(float(v), 4) for k, v in mr.items() if isinstance(v, (int, float))})

    shutil.copy(best, os.path.join(MODELS_DIR, "onion-yolov8n.pt"))
    onnx_path = model.export(format="onnx", imgsz=320, opset=12, dynamic=True, simplify=True)
    dest = os.path.join(MODELS_DIR, "onion-yolov8n.onnx")
    shutil.copy(onnx_path, dest)
    rc = os.path.join(os.path.dirname(os.path.dirname(best)), "results.csv")
    epochs_done = None
    if os.path.exists(rc):
        with open(rc) as f:
            epochs_done = max(1, len(list(csv.reader(f))) - 1)
    summary = {
        "best_weights_source": best,
        "onnx": dest,
        "val_at_export": {k: round(float(v), 4) for k, v in mr.items() if isinstance(v, (int, float))},
        "note": "early-stopped plateau export (from scratch; see METRICS.md)",
        "epochs": epochs_done, "imgsz": 320, "batch": 8,
    }
    with open(os.path.join(MODELS_DIR, "train_yolo_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("exported ->", dest)


if __name__ == "__main__":
    main()
