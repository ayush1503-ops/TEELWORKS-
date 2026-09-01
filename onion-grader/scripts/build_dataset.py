"""Dataset builder — creates the folder structure and augments your photos.

USAGE (from the project root):
    python scripts/build_dataset.py --raw path/to/raw_photos

1. Put your ORIGINAL photos in folders named by class:
       raw_photos/healthy/*.jpg
       raw_photos/rotten/*.jpg
       raw_photos/damaged/*.jpg
       raw_photos/sprouted/*.jpg
       raw_photos/undersized/*.jpg
       raw_photos/discolored/*.jpg
       raw_photos/deformed/*.jpg

2. Run this script. It:
     - creates datasets/onion_defects/classes/{class}/...
     - writes a stratified 70/15/15 train/val/test split (by copy)
     - generates AUGMENTED copies in train/ only (brightness, contrast, hue
       shift, flip, rotate, blur, noise) to simulate real procurement-centre
       conditions: different lighting, shadows, dust, cameras, orientation.

Augmented files are named <orig>_aug<k>.jpg so you can always trace them.
Val/test sets are NEVER augmented — they must stay realistic.
"""
from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

CLASSES = ["healthy", "rotten", "damaged", "sprouted", "undersized", "discolored", "deformed"]
SPLIT = {"train": 0.70, "val": 0.15, "test": 0.15}
AUGS_PER_TRAIN_IMAGE = 6


def augment(img: np.ndarray, rng: random.Random) -> np.ndarray:
    out = img
    # brightness / contrast (lighting variation)
    alpha = 1.0 + rng.uniform(-0.25, 0.25)
    beta = rng.uniform(-30, 30)
    out = cv2.convertScaleAbs(out, alpha=alpha, beta=beta)
    # gamma (shadows)
    gamma = rng.uniform(0.7, 1.4)
    lut = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)]).astype("uint8")
    out = cv2.LUT(out, lut)
    # slight hue shift (onion varieties)
    hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[:, :, 0] = (hsv[:, :, 0] + rng.randint(-8, 8)) % 180
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    # geometry: rotation + flip
    if rng.random() < 0.8:
        h, w = out.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-25, 25), rng.uniform(0.85, 1.15))
        out = cv2.warpAffine(out, m, (w, h), borderMode=cv2.BORDER_REFLECT)
    if rng.random() < 0.5:
        out = cv2.flip(out, 1)
    # blur (cheap camera) & noise (dust/sensor)
    if rng.random() < 0.5:
        out = cv2.GaussianBlur(out, (5, 5), 0)
    if rng.random() < 0.4:
        noise = np.random.normal(0, rng.uniform(4, 12), out.shape).astype(np.int16)
        out = np.clip(out.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="folder of class sub-folders with originals")
    ap.add_argument("--out", default="datasets/onion_defects")
    args = ap.parse_args()

    raw = Path(args.raw)
    out = Path(args.out)
    rng = random.Random(42)

    counts = {}
    for cls in CLASSES:
        src = raw / cls
        if not src.exists():
            print(f"[skip] {cls}: no folder in {raw}")
            continue
        files = sorted(p for p in src.iterdir()
                       if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        rng.shuffle(files)
        n = len(files)
        if n == 0:
            print(f"[skip] {cls}: empty")
            continue
        counts[cls] = n
        n_train, n_val = int(n * SPLIT["train"]), int(n * SPLIT["val"])
        splits = {"train": files[:n_train], "val": files[n_train:n_train + n_val],
                  "test": files[n_train + n_val:]}

        for split, flist in splits.items():
            dest = out / "classes" / split / cls
            dest.mkdir(parents=True, exist_ok=True)
            for p in flist:
                shutil.copy2(p, dest / p.name)

        # augment train only
        train_dest = out / "classes" / "train" / cls
        for p in splits["train"]:
            img = cv2.imread(str(p))
            if img is None:
                continue
            for k in range(AUGS_PER_TRAIN_IMAGE):
                cv2.imwrite(str(train_dest / f"{p.stem}_aug{k}.jpg"), augment(img, rng))

        print(f"[ok] {cls}: {n} originals → train {len(splits['train'])} "
              f"(×{1 + AUGS_PER_TRAIN_IMAGE} with augs) · val {len(splits['val'])} · "
              f"test {len(splits['test'])}")

    (out / "NOTES.md").write_text(
        "# Dataset provenance\n\n"
        "Collected by the project team. Record here for EVERY photo: date, place, "
        "variety, camera, lighting, and the label reason (what defect is visible "
        "and where). Split: 70/15/15 stratified by class (seed 42). Train folder "
        "contains augmentations; val/test do not.\n\n"
        f"Classes found: {counts}\n", encoding="utf-8")
    print(f"\nDataset written to {out}. Counts: {counts}")
    print("Next: python scripts/train_baseline.py")


if __name__ == "__main__":
    main()
