"""Extract real onion crops from the field photo (watershed / grid segmentation).

Source: scan_demo_52_onions.jpg - a top-down photo of an onion tray: a regular
grid of single onions separated by bright dividers, under cool lighting
(onions read blue-purple in this photo; that IS their appearance here, and the
detector is trained on exactly these pixels - no colour assumptions are faked).

Recipe:
  1. trim dead dark borders (row/col mean V < 55)
  2. onion-cell mask = saturated OR mid-dark (dividers are bright + washed)
  3. connected components -> per-cell boxes (size/shape/saturation filtered)
  4. any merged multi-onion component is split with cv2.watershed on
     distance-transform seeds (OpenCV 5-safe: watershed RETURNS the markers)
  5. square-pad with median border colour, resize to 256x256

These crops are the ONLY real onion pixels in the project. Scope: ONE field
photo, one tray, one lighting condition - stated everywhere they are used.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(HERE)
OUT_DIR = os.path.join(API_DIR, "datasets", "crops")
CROP_SIZE = 256
SEED = 26031


def trim_dark_border(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    v = hsv[..., 2].astype(np.float32)
    row_ok = v.mean(axis=1) > 55
    col_ok = v.mean(axis=0) > 55
    if row_ok.sum() < 50 or col_ok.sum() < 50:
        return img
    y0, y1 = int(np.argmax(row_ok)), int(len(row_ok) - np.argmax(row_ok[::-1]))
    x0, x1 = int(np.argmax(col_ok)), int(len(col_ok) - np.argmax(col_ok[::-1]))
    return img[y0:y1, x0:x1]


def cell_mask(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1], hsv[..., 2]
    mask = ((s > 55) | (v < 110)).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    return mask


def watershed_split(img: np.ndarray, comp_mask: np.ndarray) -> list:
    """Split a merged component into onion-sized boxes via watershed."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    sure_bg = cv2.dilate(comp_mask, k, iterations=3)
    dist = cv2.distanceTransform(comp_mask, cv2.DIST_L2, 5)
    if dist.max() <= 0:
        return []
    _, sure_fg = cv2.threshold(dist, 0.42 * dist.max(), 255, cv2.THRESH_BINARY)
    sure_fg = sure_fg.astype(np.uint8)
    unknown = cv2.subtract(sure_bg, sure_fg)
    n_cc, markers_pre = cv2.connectedComponents(sure_fg)
    markers = markers_pre + 1
    markers[unknown == 255] = 0
    markers = cv2.watershed(img, markers)  # OpenCV 5 gotcha: returns markers
    boxes = []
    for label in range(2, n_cc + 2):
        region = (markers == label).astype(np.uint8)
        if region.sum() < 2000:
            continue
        ys, xs = np.nonzero(region)
        boxes.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
    return boxes


def segment(img: np.ndarray) -> list:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = hsv[..., 1], hsv[..., 2]
    mask = cell_mask(img)
    H, W = img.shape[:2]
    n, lab, stats, cent = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)

    raw = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 2500 or area > 0.25 * H * W:
            continue
        roi = lab[y:y + h, x:x + w] == i
        smean = float(s[y:y + h, x:x + w][roi].mean())
        if smean < 45:
            continue
        raw.append((x, y, w, h, area))
    if not raw:
        return []

    med_area = float(np.median([r[4] for r in raw]))
    boxes = []
    for x, y, w, h, area in raw:
        aspect = w / max(h, 1)
        if area > 1.7 * med_area or w > 170 or h > 170:
            comp = ((lab[y:y + h, x:x + w] > 0) & (mask[y:y + h, x:x + w] > 0)).astype(np.uint8) * 255
            sub = watershed_split(img[y:y + h, x:x + w], comp)
            for bx1, by1, bx2, by2 in sub:
                boxes.append((bx1 + x, by1 + y, bx2 + x, by2 + y))
            continue
        if 0.55 <= aspect <= 1.9 and 55 <= w <= 170 and 55 <= h <= 170:
            boxes.append((x, y, x + w - 1, y + h - 1))
    return boxes


def square_pad(crop: np.ndarray) -> np.ndarray:
    h, w = crop.shape[:2]
    side = max(h, w)
    border = np.median(crop.reshape(-1, 3), axis=0).astype(np.uint8)
    out = np.zeros((side, side, 3), dtype=np.uint8)
    out[:, :] = border
    out[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = crop
    return cv2.resize(out, (CROP_SIZE, CROP_SIZE), interpolation=cv2.INTER_AREA)


def dedupe(boxes, tol=30):
    out = []
    for b in sorted(boxes, key=lambda b: (b[1], b[0])):
        x1, y1, x2, y2 = b
        if any(abs(x1 - ox1) < tol and abs(y1 - oy1) < tol for ox1, oy1, _, _ in out):
            continue
        out.append(b)
    return out


def main(src: str = None):
    candidates = [
        src,
        os.path.join(API_DIR, "..", "scan_demo_52_onions.jpg"),
        "/home/user/onion-vision-lab/scan_demo_52_onions.jpg",
        "/home/user/TEELWORKS-/onion-vision-lab/scan_demo_52_onions.jpg",
        "/home/user/TEELWORKS-/scan_demo_52_onions.jpg",
    ]
    src = next((c for c in candidates if c and os.path.exists(c)), None)
    assert src, "field photo not found"
    img = cv2.imread(src)
    assert img is not None
    img = trim_dark_border(img)
    img = cv2.bilateralFilter(img, 7, 60, 60)

    boxes = dedupe(segment(img))
    H, W = img.shape[:2]
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(OUT_DIR):
        os.remove(os.path.join(OUT_DIR, f))
    manifest = {
        "source": os.path.basename(src),
        "source_sha256": hashlib.sha256(open(src, "rb").read()).hexdigest()[:16],
        "crop_size": CROP_SIZE,
        "method": "cell mask + connected components (+ watershed split for merged cells)",
        "notes": ("real onion crops from ONE field photo (tray grid, cool lighting - onions "
                  "appear blue-purple in this photo); square-padded with median border colour"),
        "crops": [],
    }
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        pw, ph = int(0.08 * (x2 - x1)), int(0.08 * (y2 - y1))
        x1a, y1a = max(0, x1 - pw), max(0, y1 - ph)
        x2a, y2a = min(W - 1, x2 + pw), min(H - 1, y2 + ph)
        crop = img[y1a:y2a, x1a:x2a]
        png = square_pad(crop)
        name = f"crop_{i:02d}.png"
        cv2.imwrite(os.path.join(OUT_DIR, name), png)
        manifest["crops"].append({"id": name, "src_box": [int(x1a), int(y1a), int(x2a), int(y2a)],
                                  "w": int(x2a - x1a), "h": int(y2a - y1a)})
    manifest["count"] = len(manifest["crops"])
    with open(os.path.join(OUT_DIR, "crops_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"extracted {manifest['count']} crops -> {OUT_DIR}")
    return manifest["count"]


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
