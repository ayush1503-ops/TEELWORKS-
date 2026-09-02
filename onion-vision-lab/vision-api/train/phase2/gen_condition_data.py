"""Generate the CONDITION dataset: real crops + programmatic synthetic damage.

Labels are TRUE BY CONSTRUCTION: we paste the damage ourselves, so we know the
severity tier. This is honest synthetic labelling (documented as such) - it is
NOT relabeling of natural photos, and no unmeasured claim is made about field
damage.

Crop-level splits (seed fixed, disjoint by crop so the same onion never
appears in two splits):
  test 12 crops / val 8 crops / train 28 crops   (independent of YOLO splits)

Classes (status vocabulary):
  clear   -> GREEN  NO OBVIOUS VISIBLE DAMAGE
  review  -> YELLOW NEEDS REVIEW
  suspect -> RED    VISIBLE DAMAGE

Damage operators (all pixel-level, recorded per-sample):
  mold_patch   dark irregular mold-like blotch + speckle  -> Possible Mold-Like Growth
  bruise       local darkening/desaturation of real skin   -> Surface Damage / Surface Discoloration
  wrinkle      thin dark skin creases + slight desat       -> Shriveling
  sprout       green shoot strokes at the top              -> Sprouting
"""

from __future__ import annotations

import json
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(os.path.dirname(HERE))
CROPS_DIR = os.path.join(API_DIR, "datasets", "crops")
OUT_DIR = os.path.join(API_DIR, "datasets", "condition")

SIZE = 256
SEED = 26031
N_TEST, N_VAL = 12, 8
VARIANTS = {"train": 8, "val": 6, "test": 6}


def photometric(rng, img):
    out = img.astype(np.float32)
    out *= rng.uniform(0.85, 1.15)
    gamma = rng.uniform(0.85, 1.2)
    out = 255.0 * np.power(np.clip(out / 255.0, 0, 1), gamma)
    out += rng.normal(0, rng.uniform(2.0, 6.0), out.shape)
    if rng.random() < 0.4:
        k = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], np.float32) / 5
        out = cv2.filter2D(out, -1, k)
    return np.clip(out, 0, 255).astype(np.uint8)


def _blob_mask(size, cx, cy, r, rng, irregular=0.35):
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    ang = np.arctan2(ys - cy, xs - cx)
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    wob = 1.0 + irregular * (0.5 * np.sin(ang * 3 + rng.uniform(0, 6.28))
                             + 0.3 * np.sin(ang * 5 + rng.uniform(0, 6.28))
                             + 0.2 * np.sin(ang * 7 + rng.uniform(0, 6.28)))
    return np.clip((r * wob - dist) / max(4.0, r * 0.18) + 1.0, 0, 1)  # soft edge


def _blend(img, layer, alpha):
    a = alpha[..., None] if alpha.ndim == 2 else alpha
    out = img.astype(np.float32) * (1 - a) + layer.astype(np.float32) * a
    return np.clip(out, 0, 255).astype(np.uint8)


def mold_patch(rng, img, severity):
    out = img.copy()
    n_patch = 1 if severity == "mild" else int(rng.integers(2, 5))
    for _ in range(n_patch):
        cx = rng.uniform(0.28, 0.72) * SIZE
        cy = rng.uniform(0.28, 0.72) * SIZE
        r = rng.uniform(0.055, 0.095 if severity == "mild" else 0.20) * SIZE
        m = _blob_mask(SIZE, cx, cy, r, rng, irregular=0.45)
        op = rng.uniform(0.5, 0.68) if severity == "mild" else rng.uniform(0.68, 0.9)
        base = np.array([rng.uniform(28, 48), rng.uniform(42, 62), rng.uniform(28, 46)], np.float32)  # BGR moldy
        layer = base[None, None, :] + rng.normal(0, 9, (SIZE, SIZE, 3)).astype(np.float32)
        # speckle inside
        speck = (rng.random((SIZE, SIZE)) < 0.10).astype(np.float32)
        layer = layer * (1 - 0.5 * cv2.GaussianBlur(speck, (0, 0), 1.5)[..., None])
        out = _blend(out, layer, m * op)
    return out


def bruise(rng, img, severity):
    out = img.copy()
    n_patch = 1 if severity == "mild" else int(rng.integers(2, 4))
    for _ in range(n_patch):
        cx = rng.uniform(0.25, 0.75) * SIZE
        cy = rng.uniform(0.25, 0.75) * SIZE
        r = rng.uniform(0.08, 0.13) * SIZE if severity == "mild" else rng.uniform(0.13, 0.24) * SIZE
        m = _blob_mask(SIZE, cx, cy, r, rng, irregular=0.2)
        op = rng.uniform(0.35, 0.5) if severity == "mild" else rng.uniform(0.55, 0.75)
        # darken + desaturate the REAL local skin (hue-true bruising)
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] *= (1 - 0.35 * m * op)
        hsv[..., 2] *= (1 - 0.55 * m * op)
        dark = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        out = _blend(out, dark, m * op)
    return out


def wrinkle(rng, img, severity):
    out = img.copy()
    n = 3 if severity == "mild" else int(rng.integers(5, 8))
    canvas = out.astype(np.float32)
    shade = np.zeros((SIZE, SIZE), np.float32)
    for _ in range(n):
        x0, y0 = rng.uniform(0.15, 0.85) * SIZE, rng.uniform(0.1, 0.9) * SIZE
        pts = np.array([[x0 + rng.uniform(-45, 45) * t / 3, y0 + rng.uniform(-28, 28) * t / 3]
                        for t in range(4)], np.int32)
        cv2.polylines(shade, [pts], False, 1.0, int(rng.uniform(2, 4)))
    shade = cv2.GaussianBlur(shade, (0, 0), 1.2)
    canvas *= (1 - 0.35 * shade[..., None])
    # whole-crop slight drying
    hsv = cv2.cvtColor(np.clip(canvas, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= 0.88 if severity == "mild" else 0.75
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    return out


def sprout(rng, img, severity="mild"):
    out = img.copy()
    gx, gy = rng.uniform(0.35, 0.65) * SIZE, rng.uniform(0.08, 0.28) * SIZE
    canvas = out.astype(np.float32)
    green = np.array([45, 150, 70], np.float32)  # BGR fresh green
    for _ in range(int(rng.integers(2, 4))):
        dx, dy = rng.uniform(-30, 30), rng.uniform(-18, 22)
        pts = np.array([[gx + dx * t / 3, gy + dy * t / 3 + rng.uniform(-8, 8) * (t % 2)]
                        for t in range(4)], np.int32)
        cv2.polylines(canvas, [pts], False, green.tolist(), int(rng.uniform(3, 6)), cv2.LINE_AA)
    return np.clip(canvas, 0, 255).astype(np.uint8)


OPS = {
    "mold_patch": (mold_patch, ["Possible Mold-Like Growth"]),
    "bruise": (bruise, ["Surface Damage", "Surface Discoloration"]),
    "wrinkle": (wrinkle, ["Shriveling"]),
    "sprout": (sprout, ["Sprouting"]),
}


def make_sample(rng, crop, cls):
    img = photometric(rng, crop)
    ops_used, findings, severity = [], [], None
    if cls == "clear":
        pass
    elif cls == "review":
        op = rng.choice(["bruise", "mold_patch", "wrinkle", "sprout"], p=[0.38, 0.28, 0.14, 0.2])
        img = OPS[op][0](rng, img, "mild")
        ops_used = [op + ":mild"]
        findings = OPS[op][1]
    elif cls == "suspect":
        op = rng.choice(["mold_patch", "bruise"], p=[0.65, 0.35])
        img = OPS[op][0](rng, img, "heavy")
        ops_used = [op + ":heavy"]
        findings = OPS[op][1]
    return img, {"ops": ops_used, "findings": findings, "severity": severity or cls}


def main():
    with open(os.path.join(CROPS_DIR, "crops_manifest.json")) as f:
        ids = sorted(c["id"] for c in json.load(f)["crops"])
    rng = np.random.default_rng(SEED + 2)
    order = rng.permutation(len(ids))
    test_ids = [ids[i] for i in order[:N_TEST]]
    val_ids = [ids[i] for i in order[N_TEST:N_TEST + N_VAL]]
    train_ids = [ids[i] for i in order[N_TEST + N_VAL:]]
    assert len(train_ids) == len(ids) - N_TEST - N_VAL

    for f in os.listdir(OUT_DIR) if os.path.exists(OUT_DIR) else []:
        pass
    labels = {"frozen": True, "seed": SEED + 2, "classes": ["clear", "review", "suspect"],
              "splits": {}, "note": "programmatic synthetic damage on real crops; labels true by construction"}
    for split, split_ids in (("train", train_ids), ("val", val_ids), ("test", test_ids)):
        img_dir = os.path.join(OUT_DIR, split, "images")
        os.makedirs(img_dir, exist_ok=True)
        srng = np.random.default_rng(SEED + 2 + {"train": 10, "val": 20, "test": 30}[split])
        entries = []
        for cid in split_ids:
            crop = cv2.imread(os.path.join(CROPS_DIR, cid))
            for cls in ("clear", "review", "suspect"):
                for v in range(VARIANTS[split]):
                    img, meta = make_sample(srng, crop, cls)
                    name = f"{split}_{cid.replace('.png', '')}_{cls}_{v:02d}.png"
                    cv2.imwrite(os.path.join(img_dir, name), img)
                    entries.append({"image": name, "class": cls, "crop": cid, **meta})
        labels["splits"][split] = {"crops": split_ids, "n": len(entries), "entries": entries}
        print(f"{split}: {len(entries)} images from {len(split_ids)} crops")
    with open(os.path.join(OUT_DIR, "labels.json"), "w") as f:
        json.dump(labels, f, indent=2)
    print("condition dataset ->", OUT_DIR)


if __name__ == "__main__":
    main()
