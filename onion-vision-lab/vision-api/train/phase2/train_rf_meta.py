"""Phase-2 scikit-learn: HSV/texture RandomForest + LOGISTIC META-FUSION.

Signal 1  PyTorch MobileNetV2 CNN        (probabilities via ONNX runtime)
Signal 2  RandomForest, 26 HSV/texture features, probability-calibrated with
          CalibratedClassifierCV (sigmoid, 3-fold)
Signal 3  HSV heuristic rule scores (condition.py, Phase 1)

Fusion    multinomial LogisticRegression meta-learner over
          [cnn_p0..2, rf_p0..2, heu_p0..2, 6 raw cues]  (15 features)
          fitted on OUT-OF-FOLD predictions of the TRAIN split:
            * CNN OOF  : 3 folds by CROP (oof_cnn.py retrains the model per fold)
            * RF OOF   : cross_val_predict with GroupKFold by crop
          Regularization C selected on the VAL split, final TEST scored once.

Per-model AND fused metrics reported on the frozen 12-crop TEST split.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, API_DIR)

COND_DIR = os.path.join(API_DIR, "datasets", "condition")
MODELS_DIR = os.path.join(API_DIR, "models")

CLASSES = ("clear", "review", "suspect")
CUE_ORDER = ("darkRatio", "satStd", "greenTop", "paleRatio", "edgeDensity", "laplacianVar")
CUE_SCALE = {"darkRatio": 1.0, "satStd": 100.0, "greenTop": 1.0, "paleRatio": 1.0,
             "edgeDensity": 1.0, "laplacianVar": 1000.0}
META_FEATURES = ([f"cnn_p{i}" for i in range(3)] + [f"rf_p{i}" for i in range(3)] +
                 [f"heu_p{i}" for i in range(3)] + [f"cue_{c}" for c in CUE_ORDER])
C_GRID = (0.05, 0.1, 0.3, 1.0, 3.0)


def meta_vector(cnn_p, rf_p, heu_p, cues) -> np.ndarray:
    v = list(cnn_p) + list(rf_p) + list(heu_p)
    v += [cues[c] / CUE_SCALE[c] for c in CUE_ORDER]
    return np.array(v, dtype=np.float64)


def load_split(split):
    import cv2
    with open(os.path.join(COND_DIR, "labels.json")) as f:
        entries = json.load(f)["splits"][split]["entries"]
    imgs, ys, crops = [], [], []
    for e in entries:
        img = cv2.imread(os.path.join(COND_DIR, split, "images", e["image"]))
        imgs.append(img)
        ys.append(CLASSES.index(e["class"]))
        crops.append(e["crop"])
    return entries, imgs, np.array(ys), np.array(crops)


def cnn_session():
    import onnxruntime as ort
    path = os.path.join(MODELS_DIR, "condition-cnn.onnx")
    assert os.path.exists(path), "train the CNN first"
    return ort.InferenceSession(path, providers=["CPUExecutionProvider"])


def cnn_probs(sess, img, size=96):
    import cv2
    x = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], np.float32)
    std = np.array([0.229, 0.224, 0.225], np.float32)
    rgb = (rgb - mean) / std
    t = rgb.transpose(2, 0, 1)[None].astype(np.float32)
    logits = sess.run(None, {"input": t})[0][0]
    e = np.exp(logits - logits.max())
    return e / e.sum()


def rf_full(probs, classes_) -> np.ndarray:
    out = np.zeros((probs.shape[0], 3))
    for j, c in enumerate(classes_):
        out[:, int(c)] = probs[:, j]
    return out


def main():
    import joblib
    from hsv_features import feature_vector, condition_cues
    from condition import heuristic_probs
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_predict, GroupKFold
    from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report

    tr_e, tr_img, tr_y, tr_crops = load_split("train")
    va_e, va_img, va_y, _ = load_split("val")
    te_e, te_img, te_y, _ = load_split("test")
    print(f"splits: train={len(tr_y)} val={len(va_y)} test={len(te_y)}")

    # ---- Signal 2 features + calibrated RF ----
    X_tr = np.stack([feature_vector(im) for im in tr_img])
    X_va = np.stack([feature_vector(im) for im in va_img])
    X_te = np.stack([feature_vector(im) for im in te_img])

    def make_rf():
        return CalibratedClassifierCV(
            RandomForestClassifier(n_estimators=300, min_samples_leaf=2, n_jobs=2,
                                   random_state=26031),
            method="sigmoid", cv=3)

    rf = make_rf().fit(X_tr, tr_y)
    rf_va = rf_full(rf.predict_proba(X_va), rf.classes_)
    rf_te = rf_full(rf.predict_proba(X_te), rf.classes_)

    # RF out-of-fold probabilities on TRAIN (GroupKFold by crop - no crop leakage)
    rf_oof = cross_val_predict(make_rf(), X_tr, tr_y, cv=GroupKFold(n_splits=3),
                               groups=tr_crops, method="predict_proba")
    rf_oof_full = rf_full(rf_oof, np.arange(3))

    # ---- Signal 1: CNN probs (ONNX) + OOF from oof_cnn.py ----
    sess = cnn_session()
    cnn_va = np.stack([cnn_probs(sess, im) for im in va_img])
    cnn_te = np.stack([cnn_probs(sess, im) for im in te_img])
    oof_path = os.path.join(MODELS_DIR, "phase2", "cnn_oof_train.npy")
    assert os.path.exists(oof_path), "run oof_cnn.py first"
    cnn_oof = np.load(oof_path)

    # ---- Signal 3: HSV heuristic (deterministic) ----
    cues_tr = [condition_cues(im) for im in tr_img]
    cues_va = [condition_cues(im) for im in va_img]
    cues_te = [condition_cues(im) for im in te_img]
    heu_oof = np.stack([heuristic_probs(c) for c in cues_tr])
    heu_va = np.stack([heuristic_probs(c) for c in cues_va])
    heu_te = np.stack([heuristic_probs(c) for c in cues_te])

    # ---- Meta-learner: fit on TRAIN OOF, select C on VAL, score TEST once ----
    Z_tr = np.stack([meta_vector(cnn_oof[i], rf_oof_full[i], heu_oof[i], cues_tr[i])
                     for i in range(len(tr_y))])
    Z_va = np.stack([meta_vector(cnn_va[i], rf_va[i], heu_va[i], cues_va[i])
                     for i in range(len(va_y))])
    Z_te = np.stack([meta_vector(cnn_te[i], rf_te[i], heu_te[i], cues_te[i])
                     for i in range(len(te_y))])

    best = None
    for C in C_GRID:
        m = LogisticRegression(max_iter=3000, C=C).fit(Z_tr, tr_y)
        v_f1 = f1_score(va_y, m.predict(Z_va), average="macro")
        oof_f1 = f1_score(tr_y, m.predict(Z_tr), average="macro")
        print(f"  meta C={C}: train-OOF macroF1={oof_f1:.4f}  val macroF1={v_f1:.4f}")
        if best is None or v_f1 > best[1]:
            best = (C, v_f1)
    C_star, val_f1 = best
    print(f"selected C*={C_star} (val macroF1={val_f1:.4f})")

    # val-side selection record: fused vs its members on the SELECTION split
    cnn_val_f1 = f1_score(va_y, cnn_va.argmax(1), average="macro")
    rf_val_f1 = f1_score(va_y, rf_va.argmax(1), average="macro")
    heu_val_f1 = f1_score(va_y, heu_va.argmax(1), average="macro")
    print(f"val macroF1  cnn={cnn_val_f1:.4f} rf={rf_val_f1:.4f} heuristic={heu_val_f1:.4f} fused={val_f1:.4f}")

    meta = LogisticRegression(max_iter=3000, C=C_star).fit(Z_tr, tr_y)
    fused_te = meta.predict_proba(Z_te)

    def block(name, probs):
        pred = probs.argmax(1)
        return {
            "model": name,
            "accuracy": round(float(accuracy_score(te_y, pred)), 4),
            "macro_f1": round(float(f1_score(te_y, pred, average="macro")), 4),
            "confusion": confusion_matrix(te_y, pred, labels=[0, 1, 2]).tolist(),
            "per_class": classification_report(te_y, pred, target_names=list(CLASSES),
                                               output_dict=True, zero_division=0),
        }

    results = {
        "framework": "scikit-learn",
        "models": {
            "cnn_alone": block("pytorch-cnn (onnx)", cnn_te),
            "rf_alone": block("calibrated-randomforest", rf_te),
            "heuristic_alone": block("hsv-heuristic", heu_te),
            "fused": block("meta-logistic fusion (OOF stacking)", fused_te),
        },
        "features": {"n_features": X_tr.shape[1],
                     "type": "HSV stats + LBP(9) + edges + entropy (hsv_features.py)"},
        "rf": {"n_estimators": 300, "calibration": "CalibratedClassifierCV(sigmoid, cv=3)",
               "oof": "cross_val_predict + GroupKFold(3) by crop"},
        "meta": {"learner": "LogisticRegression(multinomial)",
                 "fitted_on": f"train-split OOF predictions (n={len(tr_y)}; CNN 3-fold by crop via oof_cnn.py)",
                 "C_selected_on_val": C_star, "val_macro_f1": round(float(val_f1), 4),
                 "features": META_FEATURES,
                 "coef": meta.coef_.round(3).tolist(),
                 "test_logloss": round(float(-np.log(np.clip(
                     fused_te[np.arange(len(te_y)), te_y], 1e-9, 1)).mean()), 4)},
        "selection": {
            "policy": "configuration chosen by VAL macro-F1; TEST scored once",
            "val_macro_f1": {"cnn": round(float(cnn_val_f1), 4), "rf": round(float(rf_val_f1), 4),
                             "heuristic": round(float(heu_val_f1), 4), "fused": round(float(val_f1), 4)},
            "honest_note": ("on the frozen TEST split the CNN alone may score higher than the "
                            "fusion; the fusion was selected on VAL and is served because it uses "
                            "three independent signals, but both numbers are reported rather than "
                            "hiding the comparison")},
        "fitted_on_scope": "train=28 crops (OOF), val=8 crops (model selection), test=12 frozen crops",
        "scope": ("frozen 12 test crops, programmatic synthetic damage over real crops from ONE "
                  "field photo; field validation pending"),
    }

    # serve-time latency: RF thread pools oversubscribe the 2-vCPU box against
    # onnxruntime threads; force single-threaded forests before pickling
    from sklearn.ensemble import RandomForestClassifier

    def _walk(o, seen=None, depth=0):
        seen = seen if seen is not None else set()
        if id(o) in seen or depth > 6:
            return
        seen.add(id(o))
        if isinstance(o, RandomForestClassifier):
            yield o
        if isinstance(o, (list, tuple)):
            for x in o:
                yield from _walk(x, seen, depth + 1)
        elif hasattr(o, "__dict__"):
            for v in vars(o).values():
                yield from _walk(v, seen, depth + 1)

    for forest in _walk(rf):
        forest.n_jobs = 1
    joblib.dump(rf, os.path.join(MODELS_DIR, "condition-rf.joblib"))
    joblib.dump(meta, os.path.join(MODELS_DIR, "condition-meta-lr.joblib"))
    os.makedirs(os.path.join(MODELS_DIR, "phase2"), exist_ok=True)
    with open(os.path.join(MODELS_DIR, "phase2", "condition-fusion.json"), "w") as f:
        json.dump(results, f, indent=2)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ("accuracy", "macro_f1")}
                      for k, v in results["models"].items()}, indent=2))

    # serving spot-check: ensemble.py must reproduce the fused prediction
    from ensemble import ConditionEnsemble
    ens = ConditionEnsemble(MODELS_DIR)
    n = agree = 0
    for i in range(0, len(te_img), 40):
        r = ens.predict(te_img[i])
        agree += int(r["conditionClass"] == CLASSES[int(fused_te[i].argmax())])
        n += 1
    print(f"ensemble/serving agreement spot-check: {agree}/{n}")


if __name__ == "__main__":
    main()
