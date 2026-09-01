"""SYNTHETIC onion dataset generator — ML bootstrap data, honestly labelled.

WHY: no adequate public onion-bulb dataset exists (verified — see
docs/DATASET.md) and field collection takes weeks. Synthetic bootstrapping
lets the FULL ML pipeline (train → validate → serve) run end-to-end TODAY.
The model is explicitly labelled trained_on="synthetic-v1" everywhere it is
surfaced, and every metric is quoted as "on synthetic validation data".
Replace with field data via scripts/build_dataset.py when collected — the
exact same training path is reused.

Classes: healthy, rotten, damaged, sprouted, undersized, discolored, deformed
Randomized per image: variety hue (red/pink/yellow/white), size, position,
background colour, lighting/gamma, noise, blur, rotation.

Run (project root):
    python scripts/generate_synthetic_dataset.py --out datasets/synthetic_v1 \
        --per-class 90 --size 384
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

CLASSES = ["healthy", "rotten", "damaged", "sprouted", "undersized",
           "discolored", "deformed"]

# onion skin palettes (BGR) approximating common Indian varieties
VARIETIES = [
    ((66, 42, 152), (56, 34, 138)),   # dark red (Nashik-type)
    ((70, 90, 175), (60, 76, 158)),   # red-pink
    ((60, 130, 190), (52, 112, 170)), # light pink
    ((70, 150, 205), (62, 132, 185)), # rose
    ((90, 170, 215), (80, 150, 195)), # yellow-pink
]
BACKGROUNDS = [(205, 200, 190), (215, 208, 196), (188, 192, 198),
               (222, 214, 200), (200, 195, 185)]


def _apply_capture(img: Image.Image, rng: random.Random) -> Image.Image:
    """Simulate phone capture: brightness/contrast/gamma, noise, blur."""
    arr = np.asarray(img).copy()
    alpha = 1.0 + rng.uniform(-0.18, 0.18)
    beta = rng.uniform(-22, 22)
    arr = cv2.convertScaleAbs(arr, alpha=alpha, beta=beta)
    gamma = rng.uniform(0.8, 1.3)
    lut = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)]).astype("uint8")
    arr = cv2.LUT(arr, lut)
    if rng.random() < 0.35:
        arr = cv2.GaussianBlur(arr, (5, 5), 0)
    if rng.random() < 0.5:
        noise = np.random.normal(0, rng.uniform(3, 9), arr.shape).astype(np.int16)
        arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    if rng.random() < 0.6:
        h, w = arr.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-20, 20), rng.uniform(0.9, 1.08))
        arr = cv2.warpAffine(arr, m, (w, h), borderMode=cv2.BORDER_REFLECT)
    return Image.fromarray(arr)


def synth_image(kind: str, rng: random.Random, size: int) -> Image.Image:
    bg = BACKGROUNDS[rng.randrange(len(BACKGROUNDS))]
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    body, streak = VARIETIES[rng.randrange(len(VARIETIES))]

    r = rng.randint(int(size * 0.30), int(size * 0.34))          # normal onion
    if kind == "undersized":
        r = rng.randint(int(size * 0.13), int(size * 0.17))      # small onion
    cx = size // 2 + rng.randint(-12, 12)
    cy = size // 2 + rng.randint(-6, 14)

    squash = 1.0
    if kind == "deformed":
        squash = rng.uniform(0.58, 0.74)                          # squashed bulb

    rx, ry = r, int(r * squash)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=body)
    for i in range(3):                                            # skin streaks
        d.arc([cx - rx + 8 + 6 * i, cy - ry + 10, cx + rx - 8 - 6 * i, cy + ry - 10],
              start=200, end=340, fill=streak, width=4)
    if kind == "deformed" and rng.random() < 0.5:                 # double bulb
        d.ellipse([cx - rx, cy - int(ry * 0.55), cx - int(rx * 0.15), cy + ry],
                  outline=streak, width=6)

    if kind == "rotten":                                          # dark soft patches
        for _ in range(rng.randint(2, 4)):
            w_ = rng.randint(int(r * 0.30), int(r * 0.62))
            h_ = rng.randint(int(r * 0.25), int(r * 0.55))
            ox = cx + rng.randint(-rx + w_ // 2, rx - w_ // 2)
            oy = cy + rng.randint(-ry + h_ // 2, ry - h_ // 2)
            d.ellipse([ox - w_ // 2, oy - h_ // 2, ox + w_ // 2, oy + h_ // 2],
                      fill=(rng.randint(28, 52), rng.randint(14, 24), rng.randint(10, 20)))

    if kind == "damaged":                                         # pale gashes + cut lines
        for _ in range(rng.randint(2, 4)):
            x0 = cx + rng.randint(-rx, rx - 20)
            y0 = cy + rng.randint(-ry, ry - 8)
            x1, y1 = x0 + rng.randint(22, int(r * 0.5)), y0 + rng.randint(-18, 18)
            d.line([x0, y0, x1, y1], fill=(150, 168, 190), width=rng.randint(3, 6))
            d.line([x0, y0 + 3, x1, y1 + 3], fill=(52, 40, 38), width=2)

    if kind == "sprouted":                                        # green neck shoot
        sh = rng.randint(int(r * 0.45), int(r * 0.85))
        d.polygon([(cx - 8, cy - ry + 6), (cx + 8, cy - ry + 6), (cx + rng.randint(-10, 10), cy - ry - sh)],
                  fill=(58, 158, 58))
        d.ellipse([cx - 24, cy - ry - 4, cx + 24, cy - ry + 36], fill=(70, 172, 70))

    if kind == "discolored":                                      # two-tone skin
        mask = Image.new("L", (size, size), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        pale = Image.new("RGB", (size, size), (120, 175, 205))    # pale tan half
        half = Image.new("L", (size, size), 0)
        hd = ImageDraw.Draw(half)
        hd.rectangle([0, 0, cx + rng.randint(-30, 30), size], fill=140)
        img.paste(pale, (0, 0), Image.composite(half, Image.new("L", (size, size), 0), mask))

    if kind == "healthy" and rng.random() < 0.4:                  # dust specks
        for _ in range(rng.randint(2, 5)):
            sx = cx + rng.randint(-rx + 6, rx - 6)
            sy = cy + rng.randint(-ry + 6, ry - 6)
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(90, 66, 60))

    return _apply_capture(img, rng)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/synthetic_v1")
    ap.add_argument("--per-class", type=int, default=90)
    ap.add_argument("--size", type=int, default=384)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out = Path(args.out) / "classes"
    made = {}
    for cls in CLASSES:
        for split, share in (("train", 0.70), ("val", 0.15), ("test", 0.15)):
            n = int(args.per_class * share)
            for i in range(n):
                dest = out / split / cls
                dest.mkdir(parents=True, exist_ok=True)
                synth_image(cls, rng, args.size).save(dest / f"{cls}_{split}_{i:03d}.jpg",
                                                      quality=90)
        made[cls] = args.per_class

    (Path(args.out) / "NOTES.md").write_text(
        "# SYNTHETIC dataset (synthetic-v1)\n\n"
        "Generated programmatically by scripts/generate_synthetic_dataset.py "
        f"(seed {args.seed}). NOT field data. Used to bootstrap the ML pipeline; "
        "all resulting metrics are 'on synthetic data' and are labelled as such "
        "in the app. Replace with field data via scripts/build_dataset.py.\n\n"
        f"Per class: {made}\n", encoding="utf-8")
    print(f"synthetic-v1 written to {args.out} — {len(CLASSES)} classes × "
          f"{args.per_class} = {len(CLASSES) * args.per_class} images")


if __name__ == "__main__":
    main()
