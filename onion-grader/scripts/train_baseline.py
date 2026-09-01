"""Train the BASELINE classifier (RandomForest) on a real dataset folder.

Works for BOTH dataset types:
  * field data  — scripts/build_dataset.py → datasets/onion_defects
  * synthetic   — scripts/generate_synthetic_dataset.py → datasets/synthetic_v1

The model learns to predict the defect class from the SAME measured features
the rule engine uses → stays explainable (feature importances) and trains in
seconds on CPU. Output: models/classifier.pkl — the backend auto-detects it
and records what it was trained on + its measured validation accuracy.

REFUSES to train without a real dataset folder (no fake data, ever).

Run from the project root:
    python scripts/train_baseline.py --dataset datasets/synthetic_v1 --label synthetic-v1
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "backend"))

from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.metrics import (accuracy_score, classification_report,  # noqa: E402
                             confusion_matrix)

from app.services import preprocessing as pre  # noqa: E402
from app.services.features import FEATURE_ORDER, extract_features  # noqa: E402
from app.services.grading import DEFAULT_RULES  # noqa: E402

MODEL_OUT = PROJECT / "models" / "classifier.pkl"


def features_for(path: Path):
    img = pre.load_bgr(path.read_bytes())
    if img is None:
        return None
    det = pre.segment_onion(img, DEFAULT_RULES)
    if not det.found:
        return None
    return extract_features(det, DEFAULT_RULES)


def collect(ds: Path, split: str):
    X, y, skipped = [], [], 0
    split_dir = ds / "classes" / split
    if not split_dir.exists():
        return X, y, skipped
    for cls_dir in sorted(split_dir.iterdir()):
        if not cls_dir.is_dir():
            continue
        for p in sorted(cls_dir.glob("*.jpg")):
            f = features_for(p)
            if f is None:
                skipped += 1
                continue
            X.append(f.vector())
            y.append(cls_dir.name)
    return X, y, skipped


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=str(PROJECT / "datasets" / "onion_defects"))
    ap.add_argument("--label", default="field-v1",
                    help="honest label recorded with the model (e.g. synthetic-v1)")
    args = ap.parse_args()
    ds = Path(args.dataset)

    if not (ds / "classes" / "train").exists():
        sys.exit(
            f"No dataset found at {ds}/classes/train.\n"
            "Refusing to train on nothing (honesty rule).\n"
            "  field data:    python scripts/build_dataset.py --raw raw_photos\n"
            "  synthetic:     python scripts/generate_synthetic_dataset.py "
            "--out datasets/synthetic_v1\n"
            "then re-run with --dataset <path> --label <label>."
        )

    Xtr, ytr, sk_tr = collect(ds, "train")
    Xva, yva, sk_va = collect(ds, "val")
    print(f"train: {len(Xtr)} samples (skipped {sk_tr}: not detected) · "
          f"val: {len(Xva)} (skipped {sk_va})")
    if len(Xtr) < 20 or len(set(ytr)) < 2:
        sys.exit("Too little usable training data. Need ≥20 samples across ≥2 classes.")

    model = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                   random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)

    val_acc = None
    if Xva:
        pred = model.predict(Xva)
        val_acc = round(float(accuracy_score(yva, pred)), 4)
        print(f"\nValidation accuracy ({args.label}): {val_acc}")
        print(classification_report(yva, pred, zero_division=0))
        labels = sorted(set(yva) | set(pred))
        cm = confusion_matrix(yva, pred, labels=labels)
        print("Confusion matrix (rows = actual):")
        print("          " + "  ".join(f"{l[:9]:>9}" for l in labels))
        for lbl, row in zip(labels, cm):
            print(f"{lbl[:9]:>9}  " + "  ".join(f"{v:>9}" for v in row))
        print(f"\nQuote this ONLY as '{args.label} validation accuracy' — never as "
              "general field accuracy.")
    else:
        print("No validation split — no metric is claimed.")

    imp = sorted(zip(FEATURE_ORDER, model.feature_importances_),
                 key=lambda t: -t[1])[:8]
    print("\nTop feature importances (explainability):")
    for name, score in imp:
        print(f"  {name:<24} {score:.3f}")

    # per-class feature statistics → used at inference to explain WHY a sample
    # is classified away from healthy (z-scored drivers)
    import numpy as np
    stats: dict[str, dict[str, tuple[float, float]]] = {}
    Xtr_arr = np.asarray(Xtr, dtype=float)
    for cls in sorted(set(ytr)):
        rows = Xtr_arr[[i for i, yy in enumerate(ytr) if yy == cls]]
        stats[cls] = {name: (round(float(rows[:, j].mean()), 3),
                             round(float(rows[:, j].std()) + 1e-6, 3))
                      for j, name in enumerate(FEATURE_ORDER)}

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_OUT, "wb") as fh:
        pickle.dump({"model": model, "labels": list(model.classes_),
                     "feature_keys": FEATURE_ORDER, "trained_on": args.label,
                     "val_accuracy": val_acc, "n_train": len(Xtr),
                     "algorithm": "RandomForest(300)", "class_stats": stats}, fh)
    print(f"\nSaved → {MODEL_OUT}")
    print(f"trained_on='{args.label}' is stamped into the model; the backend "
          "surfaces it in every analysis (model block).")


if __name__ == "__main__":
    main()
