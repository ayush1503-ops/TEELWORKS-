"""v1 dataset generator: copy-paste augmentation scenes from real crops.

Scene = procedural background + 1..5 pasted REAL onion crops (rotation,
scale, soft shadow) with YOLO labels. Honest scope: positives are composites
of the same 33 train-pool crops from ONE field photo.

Split discipline (crop-level, frozen):
  * 9 crops are HELD OUT for the frozen test set (make_dataset2.py)
  * of the remaining 39: 33 for train scenes, 6 for val scenes

All randomness is seeded - the dataset is reproducible.
"""

from __future__ import annotations

import hashlib
import json
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(HERE)
CROPS_DIR = os.path.join(API_DIR, "datasets", "crops")
SCENES_DIR = os.path.join(API_DIR, "datasets", "scenes")
CROP_SIZE = 256

CANVAS = 640
SEED = 26031
N_TEST_CROPS = 9          # frozen held-out crops for the benchmark
N_TRAIN_SCENES = 520
N_VAL_SCENES = 130
VAL_POOL_CROPS = 6        # crops used only in val scenes

BACKGROUNDS = [
    ("jute", (96, 118, 72), (120, 148, 94)),      # BGR beige-green sack
    ("wood", (58, 72, 96), (42, 52, 74)),         # brown planks
    ("concrete", (105, 108, 112), (128, 132, 136)),
    ("tarp", (40, 60, 150), (60, 84, 176)),       # blue tarp
    ("sack_white", (150, 165, 175), (185, 198, 205)),
]


def make_background(rng: np.random.Generator) -> np.ndarray:
    name, c_top, c_bot = BACKGROUNDS[rng.integers(len(BACKGROUNDS))]
    canvas = np.zeros((CANVAS, CANVAS, 3), dtype=np.float32)
    t = np.linspace(0, 1, CANVAS)[:, None]
    for ch in range(3):
        canvas[..., ch] = c_top[ch] + (c_bot[ch] - c_top[ch]) * t
    # grain
    canvas += rng.normal(0, 6, canvas.shape)
    if name == "wood":
        for y in range(0, CANVAS, rng.integers(60, 110)):
            canvas[y:y + 3] *= 0.82
    if name == "jute":
        xs = np.arange(CANVAS)
        weave = (np.sin(xs / 4.0) * 5)[None, :]
        canvas += weave[..., None]
    # vignette
    yy, xx = np.mgrid[0:CANVAS, 0:CANVAS]
    r = np.sqrt((xx - CANVAS / 2) ** 2 + (yy - CANVAS / 2) ** 2) / (CANVAS * 0.72)
    vign = np.clip(1 - 0.35 * r ** 2, 0.65, 1)[..., None]
    canvas = np.clip(canvas * vign, 0, 255).astype(np.uint8)
    return canvas


def rotate_crop(crop: np.ndarray, angle: float, scale: float) -> np.ndarray:
    h, w = int(crop.shape[0]), int(crop.shape[1])
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    return cv2.warpAffine(crop, M, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_REPLICATE)


def paste_with_shadow(canvas: np.ndarray, crop: np.ndarray, cx: int, cy: int):
    h, w = crop.shape[:2]
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    # soft elliptical shadow
    sh = canvas.copy()
    axes = (int(w * 0.55), int(h * 0.22))
    cv2.ellipse(sh, (int(cx), int(min(canvas.shape[0] - 2, y1 + h))), axes, 0, 0, 360, (0, 0, 0), -1)
    cv2.addWeighted(sh, 0.35, canvas, 0.65, 0, canvas)
    # alpha paste: crop corners are median-padded; use a soft circular mask
    mask = np.full((h, w), 255, np.uint8)
    cv2.ellipse(mask, (w // 2, h // 2), (w // 2 - 2, h // 2 - 2), 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    x1c, y1c = max(0, x1), max(0, y1)
    x2c, y2c = min(canvas.shape[1], x1 + w), min(canvas.shape[0], y1 + h)
    mx, my = x1c - x1, y1c - y1
    roi = canvas[y1c:y2c, x1c:x2c]
    cm = mask[my:my + roi.shape[0], mx:mx + roi.shape[1]].astype(np.float32) / 255.0
    src = crop[my:my + roi.shape[0], mx:mx + roi.shape[1]].astype(np.float32)
    canvas[y1c:y2c, x1c:x2c] = (src * cm[..., None] + roi.astype(np.float32) * (1 - cm[..., None])).astype(np.uint8)


def make_scene(rng: np.random.Generator, pool: list, n_min: int, n_max: int):
    canvas = make_background(rng)
    n = int(rng.integers(n_min, n_max + 1))
    labels = []
    picks = rng.choice(len(pool), size=n, replace=(n > len(pool)))
    # paste from back (top) to front (bottom) like a pile
    placed = []
    for idx in picks:
        crop = pool[int(idx)]
        scale = float(rng.uniform(0.42, 0.92))
        angle = float(rng.uniform(-28, 28))
        w = int(CROP_SIZE * scale)
        warped = cv2.resize(rotate_crop(crop, angle, 1.0), (w, w), interpolation=cv2.INTER_AREA)
        cx = int(rng.integers(w // 2 + 4, CANVAS - w // 2 - 4))
        cy = int(rng.integers(w // 2 + 4, CANVAS - w // 2 - 4))
        paste_with_shadow(canvas, warped, cx, cy)
        placed.append((cx, cy, w))
    for cx, cy, w in placed:
        labels.append([0.0, cx / CANVAS, cy / CANVAS, w / CANVAS, w / CANVAS])
    return canvas, labels


def load_split():
    with open(os.path.join(CROPS_DIR, "crops_manifest.json")) as f:
        manifest = json.load(f)
    ids = sorted(c["id"] for c in manifest["crops"])
    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(ids))
    test_ids = [ids[i] for i in order[:N_TEST_CROPS]]
    pool_ids = [ids[i] for i in order[N_TEST_CROPS:]]
    val_ids = pool_ids[-VAL_POOL_CROPS:]
    train_ids = pool_ids[:-VAL_POOL_CROPS]
    return ids, train_ids, val_ids, test_ids


def write_split(split: str, scenes: int, pool_ids: list, seed_offset: int):
    rng = np.random.default_rng(SEED + seed_offset)
    img_dir = os.path.join(SCENES_DIR, split, "images")
    lbl_dir = os.path.join(SCENES_DIR, split, "labels")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)
    pool = [cv2.imread(os.path.join(CROPS_DIR, i)) for i in pool_ids]
    for k in range(scenes):
        img, labels = make_scene(rng, pool, 1, 5)
        name = f"{split}_{k:04d}"
        cv2.imwrite(os.path.join(img_dir, name + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(os.path.join(lbl_dir, name + ".txt"), "w") as f:
            for l in labels:
                f.write(" ".join(f"{v:.6f}" for v in l) + "\n")
    print(f"{split}: {scenes} scenes ({len(pool_ids)} crops)")


def main():
    ids, train_ids, val_ids, test_ids = load_split()
    print(f"crops total={len(ids)} train_pool={len(train_ids)} val_pool={len(val_ids)} test_held={len(test_ids)}")
    write_split("train", N_TRAIN_SCENES, train_ids, 0)
    write_split("val", N_VAL_SCENES, val_ids, 1)
    # dataset.yaml (v1 - positives only; v2 adds hard negatives)
    yaml_path = os.path.join(SCENES_DIR, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {SCENES_DIR}\ntrain: train/images\nval: val/images\ntest: test/images\n"
                f"nc: 1\nnames: ['onion']\n")
    split_info = {
        "seed": SEED, "all_crops": ids, "train_pool": train_ids,
        "val_pool": val_ids, "test_held_out": test_ids,
        "canvas": CANVAS,
        "v1": {"train": N_TRAIN_SCENES, "val": N_VAL_SCENES},
    }
    with open(os.path.join(SCENES_DIR, "splits.json"), "w") as f:
        json.dump(split_info, f, indent=2)
    print("v1 dataset written:", SCENES_DIR)


if __name__ == "__main__":
    main()
