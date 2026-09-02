"""v2 dataset generator: 400 hard negatives + FROZEN test set.

Hard negatives = distractor-only scenes built from PROCEDURAL look-alikes
(shaded tomato/potato/garlic-coloured blobs with speculars - deliberately
NOT onion-textured). They teach the detector to reject colour-matched clutter.

The FROZEN test set is generated once with a fixed seed and never touched
again:
  * 130 positive scenes built ONLY from the 9 held-out crops
  * 40 distractor-only negatives (fresh distractor seeds)
Benchmark discipline: no test crop or test distractor appears in training.
"""

from __future__ import annotations

import hashlib
import json
import os

import cv2
import numpy as np

from make_dataset import (HERE, API_DIR, SCENES_DIR, CANVAS, SEED, load_split,
                          make_background, paste_with_shadow, N_TEST_CROPS)

N_HARD_NEG_TRAIN = 400
N_HARD_NEG_VAL = 40
N_TEST_POS = 130
N_TEST_NEG = 40

DISTRACTOR_PALETTES = [
    ("tomato", (2, 8), (150, 220), (90, 150)),      # hue deg range, sat, val
    ("potato", (22, 34), (60, 120), (110, 180)),
    ("garlic", (18, 30), (20, 55), (150, 210)),
    ("apple", (348, 372), (120, 200), (100, 170)),  # hue wraps at 360
]


def make_distractor(rng: np.random.Generator, size: int) -> np.ndarray:
    """Procedural non-onion blob: radially shaded sphere with specular.

    Deliberately smooth / waxy - no onion skin streaks or papery texture.
    """
    name, (h0, h1), (s0, s1), (v0, v1) = DISTRACTOR_PALETTES[rng.integers(len(DISTRACTOR_PALETTES))]
    hue = (rng.uniform(h0, h1) % 360.0) / 2.0  # OpenCV hue units
    sat = rng.uniform(s0, s1)
    val = rng.uniform(v0, v1)
    side = size
    yy, xx = np.mgrid[0:side, 0:side].astype(np.float32)
    cx, cy = side / 2, side / 2
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (side / 2)
    squash_y = rng.uniform(0.85, 1.0)
    r = np.sqrt((xx - cx) ** 2 + ((yy - cy) / squash_y) ** 2) / (side / 2)
    inside = r <= 1.0
    shade = np.clip(1 - 0.55 * r, 0.35, 1.0)
    hue_arr = np.full((side, side), hue, np.float32)
    sat_arr = np.clip(sat * (0.55 + 0.45 * shade), 0, 255)
    val_arr = np.clip(val * shade, 0, 255)
    # specular highlight
    sx, sy = side * rng.uniform(0.35, 0.45), side * rng.uniform(0.3, 0.42)
    spec = np.exp(-(((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * (side / 12) ** 2))) * rng.uniform(70, 120)
    val_arr = np.clip(val_arr + spec, 0, 255)
    hsv = np.stack([hue_arr, sat_arr, val_arr], -1).astype(np.uint8)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    bgr += rng.normal(0, 3.5, bgr.shape).astype(np.float32).astype(np.int16).astype(np.uint8)
    mask = (inside * 255).astype(np.uint8)
    if name == "garlic":
        mask = cv2.ellipse(mask, (side // 2, side // 2), (side // 2 - 2, side // 2 - 4), 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (7, 7), 0)
    out = np.zeros((side, side, 3), np.uint8)
    for ch in range(3):
        out[..., ch] = (bgr[..., ch] * (mask / 255.0)).astype(np.uint8)
    alpha = mask.astype(np.float32) / 255.0
    return out, alpha


def paste_alpha(canvas: np.ndarray, blob: np.ndarray, alpha: np.ndarray, cx: int, cy: int):
    h, w = blob.shape[:2]
    x1, y1 = int(cx - w / 2), int(cy - h / 2)
    x1c, y1c = max(0, x1), max(0, y1)
    x2c, y2c = min(canvas.shape[1], x1 + w), min(canvas.shape[0], y1 + h)
    if x2c <= x1c or y2c <= y1c:
        return
    mx, my = x1c - x1, y1c - y1
    roi = canvas[y1c:y2c, x1c:x2c].astype(np.float32)
    a = alpha[my:my + roi.shape[0], mx:mx + roi.shape[1]][..., None]
    src = blob[my:my + roi.shape[0], mx:mx + roi.shape[1]].astype(np.float32)
    canvas[y1c:y2c, x1c:x2c] = (src * a + roi * (1 - a)).astype(np.uint8)


def make_negative_scene(rng: np.random.Generator, n_min=2, n_max=7):
    canvas = make_background(rng)
    n = int(rng.integers(n_min, n_max + 1))
    for _ in range(n):
        size = int(rng.integers(70, 240))
        blob, alpha = make_distractor(rng, size)
        cx = int(rng.integers(size // 2 + 4, CANVAS - size // 2 - 4))
        cy = int(rng.integers(size // 2 + 4, CANVAS - size // 2 - 4))
        paste_alpha(canvas, blob, alpha, cx, cy)
    return canvas


def write_negatives(split: str, count: int, seed_offset: int):
    rng = np.random.default_rng(SEED + seed_offset)
    img_dir = os.path.join(SCENES_DIR, split, "images")
    lbl_dir = os.path.join(SCENES_DIR, split, "labels")
    start = 10_000 if split == "train" else 20_000
    for k in range(count):
        canvas = make_negative_scene(rng)
        name = f"{split}_{start + k:04d}"
        cv2.imwrite(os.path.join(img_dir, name + ".jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 92])
        open(os.path.join(lbl_dir, name + ".txt"), "w").close()
    print(f"{split}: +{count} distractor-only hard negatives")


def main():
    ids, train_ids, val_ids, test_ids = load_split()
    # ---- v2: hard negatives into train + val (labels empty) ----
    write_negatives("train", N_HARD_NEG_TRAIN, 100)
    write_negatives("val", N_HARD_NEG_VAL, 101)

    # ---- FROZEN test ----
    rng = np.random.default_rng(SEED + 999)
    from make_dataset import make_scene
    pool = [cv2.imread(os.path.join(API_DIR, "datasets", "crops", i)) for i in test_ids]
    img_dir = os.path.join(SCENES_DIR, "test", "images")
    lbl_dir = os.path.join(SCENES_DIR, "test", "labels")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)
    manifest = {"frozen": True, "seed": SEED + 999, "positives": [], "negatives": [],
                "iou_threshold": 0.5, "conf_threshold": 0.45,
                "note": "130 positive scenes from 9 held-out crops + 40 distractor-only negatives"}
    for k in range(N_TEST_POS):
        img, labels = make_scene(rng, pool, 1, 5)
        name = f"test_{k:04d}"
        cv2.imwrite(os.path.join(img_dir, name + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        with open(os.path.join(lbl_dir, name + ".txt"), "w") as f:
            for l in labels:
                f.write(" ".join(f"{v:.6f}" for v in l) + "\n")
        manifest["positives"].append({"image": name + ".jpg",
                                      "sha256": hashlib.sha256(cv2.imencode(".jpg", img)[1].tobytes()).hexdigest()[:12],
                                      "boxes": len(labels)})
    for k in range(N_TEST_NEG):
        img = make_negative_scene(rng)
        name = f"testn_{k:04d}"
        cv2.imwrite(os.path.join(img_dir, name + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        open(os.path.join(lbl_dir, name + ".txt"), "w").close()
        manifest["negatives"].append({"image": name + ".jpg", "boxes": 0})
    with open(os.path.join(SCENES_DIR, "frozen_test_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    # save one negative for the browser e2e distractor check
    e2e_dir = os.path.join(API_DIR, "..", "e2e")
    os.makedirs(e2e_dir, exist_ok=True)
    cv2.imwrite(os.path.join(e2e_dir, "distractor.png"), make_negative_scene(np.random.default_rng(7)))
    print(f"FROZEN test: {N_TEST_POS} positives + {N_TEST_NEG} negatives -> {SCENES_DIR}/test")
    print("v2 hard negatives complete")


if __name__ == "__main__":
    main()
