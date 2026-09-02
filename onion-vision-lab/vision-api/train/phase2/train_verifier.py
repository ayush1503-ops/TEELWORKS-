"""Phase-2 TensorFlow/Keras: binary ONION vs NOT-ONION verifier.

Second-stage gate applied to every YOLO detection crop to kill residual false
positives (colour-matched look-alikes).

Data (honest, no leakage):
  positives = real crops (38 train / 10 test held-out crops, mild photometric
              augs) - the ONLY real onion pixels in the project
  negatives = procedural look-alike blobs (same generator family as the
              dataset hard negatives, FRESH seeds) + plain backgrounds +
              bright low-saturation washes, all cropped to mimic SERVING
              conditions (detection-style windows around a blob)

Export: Keras SavedModel (models/verifier_savedmodel) + ONNX conversion for
serving (tf2onnx) so the API process stays on onnxruntime. CPU-only, batch 8.
"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np
import cv2
import tensorflow as tf

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(API_DIR, "train"))
CROPS_DIR = os.path.join(API_DIR, "datasets", "crops")
MODELS_DIR = os.path.join(API_DIR, "models")

SIZE = 96
BATCH = 8
EPOCHS = int(os.environ.get("VER_EPOCHS", "10"))
SEED = 26031


def augment(rng, img):
    out = img.astype(np.float32)
    out *= rng.uniform(0.8, 1.2)
    if rng.random() < 0.5:
        out = out[:, ::-1]
    ang = rng.uniform(-14, 14)
    M = cv2.getRotationMatrix2D((SIZE / 2, SIZE / 2), ang, rng.uniform(0.9, 1.1))
    out = cv2.warpAffine(out, M, (SIZE, SIZE), borderMode=cv2.BORDER_REFLECT)
    out += rng.normal(0, 4, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def make_negatives(rng, count):
    """Procedural look-alikes (tomato/potato/garlic-coloured shaded blobs) on
    varied backgrounds - deliberately NOT onion-textured.

    Crops mimic SERVING conditions: the verifier receives YOLO detection crops
    (a window ~1.1-1.6x the blob size around its centre, resized to 96px), so
    negatives here are built the same way - full look-alike blobs, not raw
    background fragments (that scale mismatch taught an early version a
    shortcut; see METRICS.md history note).
    """
    from make_dataset2 import make_distractor, make_background, paste_alpha
    from make_dataset import CANVAS
    out = []
    while len(out) < count:
        if rng.random() < 0.25:
            # plain background "detection" (scale-matched window)
            canvas = make_background(rng)
            side = int(rng.integers(150, 300))
            y0 = int(rng.integers(0, CANVAS - side))
            x0 = int(rng.integers(0, CANVAS - side))
            out.append(cv2.resize(canvas[y0:y0 + side, x0:x0 + side], (SIZE, SIZE)))
            continue
        if rng.random() < 0.15:
            # bright low-saturation wash (tray dividers, paper, overexposed floor)
            v = rng.uniform(140, 235)
            wash = np.full((CANVAS, CANVAS, 3), v, np.float32)
            wash += rng.normal(0, 5, wash.shape)
            wash *= np.linspace(0.9, 1.08, CANVAS)[:, None, None]
            side = int(rng.integers(150, 300))
            y0 = int(rng.integers(0, CANVAS - side))
            x0 = int(rng.integers(0, CANVAS - side))
            out.append(cv2.resize(np.clip(wash, 0, 255)[y0:y0 + side, x0:x0 + side]
                                  .astype(np.uint8), (SIZE, SIZE)))
            continue
        canvas = make_background(rng)
        n = int(rng.integers(1, 4))
        centers = []
        for _ in range(n):
            s = int(rng.integers(110, 320))
            blob, alpha = make_distractor(rng, s)
            cx = int(rng.integers(s // 2 + 2, CANVAS - s // 2 - 2))
            cy = int(rng.integers(s // 2 + 2, CANVAS - s // 2 - 2))
            paste_alpha(canvas, blob, alpha, cx, cy)
            centers.append((cx, cy, s))
        cx, cy, s = centers[int(rng.integers(0, len(centers)))]
        side = int(s * rng.uniform(1.1, 1.6))
        half = side // 2
        y0 = int(np.clip(cy - half, 0, CANVAS - side))
        x0 = int(np.clip(cx - half, 0, CANVAS - side))
        out.append(cv2.resize(canvas[y0:y0 + side, x0:x0 + side], (SIZE, SIZE)))
    return out


def build_model():
    inp = tf.keras.Input((SIZE, SIZE, 3))
    x = tf.keras.layers.Rescaling(1.0 / 255)(inp)
    for ch in (32, 64, 128, 256):
        x = tf.keras.layers.Conv2D(ch, 3, padding="same", use_bias=False)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Activation("relu")(x)
        x = tf.keras.layers.MaxPooling2D()(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    m = tf.keras.Model(inp, out, name="onion_verifier")
    m.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="binary_crossentropy",
              metrics=[tf.keras.metrics.BinaryAccuracy(name="acc"), tf.keras.metrics.AUC(name="auc")])
    return m


def load_data():
    with open(os.path.join(CROPS_DIR, "crops_manifest.json")) as f:
        ids = sorted(c["id"] for c in json.load(f)["crops"])
    rng = np.random.default_rng(SEED + 5)
    order = rng.permutation(len(ids))
    test_ids = [ids[i] for i in order[:10]]
    train_ids = [ids[i] for i in order[10:]]

    def pos_set(split_ids, n_aug, r):
        X = []
        for cid in split_ids:
            img = cv2.imread(os.path.join(CROPS_DIR, cid))
            X.append(img)
            for _ in range(n_aug - 1):
                X.append(augment(r, img))
        return X

    r_tr, r_te = np.random.default_rng(SEED + 51), np.random.default_rng(SEED + 52)
    Xp_tr = pos_set(train_ids, 8, r_tr)
    Xp_te = pos_set(test_ids, 8, r_te)
    Xn_tr = make_negatives(np.random.default_rng(SEED + 53), len(Xp_tr))
    Xn_val = make_negatives(np.random.default_rng(SEED + 54), 40)
    Xp_val = pos_set(train_ids[::4], 1, np.random.default_rng(SEED + 55))
    Xn_te = make_negatives(np.random.default_rng(SEED + 56), len(Xp_te))

    def stack(X):
        arr = np.zeros((len(X), SIZE, SIZE, 3), np.float32)
        for i, im in enumerate(X):
            arr[i] = cv2.resize(im, (SIZE, SIZE)) if im.shape[:2] != (SIZE, SIZE) else im
        return arr

    def mix(pos, neg):
        X = np.concatenate([stack(pos), stack(neg)]).astype(np.float32)
        y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))]).astype(np.float32)
        idx = np.random.default_rng(0).permutation(len(X))
        return X[idx], y[idx]

    return mix(Xp_tr, Xn_tr), mix(Xp_val, Xn_val), mix(Xp_te, Xn_te), len(train_ids), len(test_ids)


def main():
    t0 = time.time()
    (Xtr, ytr), (Xva, yva), (Xte, yte), n_tr, n_te = load_data()
    print(f"train={len(Xtr)} (pos={int(ytr.sum())}) val={len(Xva)} test={len(Xte)} "
          f"train_crops={n_tr} test_crops={n_te}", flush=True)

    model = build_model()
    model.summary()
    hist = model.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=EPOCHS, batch_size=BATCH,
                     verbose=2, shuffle=True)
    te = model.evaluate(Xte, yte, verbose=0, return_dict=True)

    # threshold selection on val: keep verifier recall on TRUE onions >= 0.995
    pv = model.predict(Xva, batch_size=BATCH).ravel()
    pos_scores = pv[yva == 1]
    tau = float(min(0.5, np.quantile(pos_scores, 0.005)))
    recall_at_tau = float((pos_scores >= tau).mean())
    neg_scores = pv[yva == 0]
    fpr_at_tau = float((neg_scores >= tau).mean())

    pt = model.predict(Xte, batch_size=BATCH).ravel()
    tp = int(((pt >= tau) & (yte == 1)).sum()); fn = int(((pt < tau) & (yte == 1)).sum())
    fp = int(((pt >= tau) & (yte == 0)).sum()); tn = int(((pt < tau) & (yte == 0)).sum())

    # ---- export SavedModel ----
    sm_dir = os.path.join(MODELS_DIR, "verifier_savedmodel")
    model.export(sm_dir)  # TF SavedModel
    print("SavedModel ->", sm_dir)

    # ---- ONNX conversion for serving ----
    import tf2onnx
    onnx_path = os.path.join(MODELS_DIR, "verifier.onnx")
    spec = (tf.TensorSpec((None, SIZE, SIZE, 3), tf.float32, name="input"),)
    model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=onnx_path)
    print("ONNX ->", onnx_path)

    # parity check
    import onnxruntime as ort
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    ort_out = sess.run(None, {"input": Xte[:8]})[0].ravel()
    keras_out = model.predict(Xte[:8], verbose=0).ravel()
    parity = float(np.abs(ort_out - keras_out).max())

    result = {
        "framework": "tensorflow",
        "model": "small CNN 4xConv+BN, binary onion/not-onion",
        "params": int(model.count_params()),
        "imgsz": SIZE, "batch": BATCH, "epochs": EPOCHS,
        "train_seconds": round(time.time() - t0, 1),
        "data": {"train_pos": int(ytr.sum()), "train_neg": int(len(ytr) - ytr.sum()),
                 "test_pos": int(yte.sum()), "test_neg": int(len(yte) - yte.sum()),
                 "train_crops": n_tr, "test_crops_held_out": n_te,
                 "negative_source": "procedural look-alike blobs + plain backgrounds + bright washes (fresh seeds, serving-matched crops)"},
        "test_binary_acc": round(float(te["acc"]), 4), "test_auc": round(float(te["auc"]), 4),
        "gate_threshold": round(tau, 4),
        "val_recall_at_tau": round(recall_at_tau, 4),
        "val_fpr_at_tau": round(fpr_at_tau, 4),
        "test_confusion_at_tau": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "onnx_parity_maxdiff": parity,
        "epochs_history": {k: [round(float(v), 4) for v in vs] for k, vs in hist.history.items()},
        "scope": ("held-out 10 real test crops x8 augs vs fresh-seed procedural distractors; "
                  "negatives are SYNTHETIC look-alikes, not photographs of real produce"),
    }
    os.makedirs(os.path.join(MODELS_DIR, "phase2"), exist_ok=True)
    with open(os.path.join(MODELS_DIR, "phase2", "verifier.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in ("test_binary_acc", "test_auc", "gate_threshold",
                                             "val_recall_at_tau", "val_fpr_at_tau",
                                             "test_confusion_at_tau", "onnx_parity_maxdiff")}, indent=2))


if __name__ == "__main__":
    main()
