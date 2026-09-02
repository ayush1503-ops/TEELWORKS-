"""Phase-2 condition ensemble: CNN (PyTorch->ONNX) + RandomForest (sklearn)
+ HSV heuristic, fused by a calibrated logistic meta-learner.

Every model was trained/measured in train/phase2 (see METRICS.md for scopes).
If any artefact is missing, the ensemble degrades honestly to whichever
signals ARE available and says so in `available` - it never fakes a signal.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

import cv2
import numpy as np
import onnxruntime as ort

from hsv_features import condition_cues, feature_vector, FEATURE_VERSION
from condition import STATUS_VOCAB, derive_findings, damage_regions

CONDITION_CLASSES = ("clear", "review", "suspect")
CUE_VECTOR = ("darkRatio", "satStd", "greenTop", "paleRatio", "edgeDensity", "laplacianVar")

ENSEMBLE_VERSION = "condition-ensemble-v2.0"

# Canonical meta-learner feature order - MUST mirror train/phase2/train_rf_meta.py
CUE_ORDER = ("darkRatio", "satStd", "greenTop", "paleRatio", "edgeDensity", "laplacianVar")
CUE_SCALE = {"darkRatio": 1.0, "satStd": 100.0, "greenTop": 1.0, "paleRatio": 1.0,
             "edgeDensity": 1.0, "laplacianVar": 1000.0}
META_FEATURES = ([f"cnn_p{i}" for i in range(3)] + [f"rf_p{i}" for i in range(3)] +
                 [f"heu_p{i}" for i in range(3)] + [f"cue_{c}" for c in CUE_ORDER])


def meta_vector(cnn_p, rf_p, heu_p, cues) -> np.ndarray:
    v = list(cnn_p) + list(rf_p) + list(heu_p)
    v += [cues[c] / CUE_SCALE[c] for c in CUE_ORDER]
    return np.array(v, dtype=np.float64)


def _to_cnn_input(bgr: np.ndarray, size: int = 96) -> np.ndarray:
    img = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    # Same normalisation as training (ImageNet mean/std on 0..1 RGB)
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    rgb = (rgb - mean) / std
    return rgb.transpose(2, 0, 1)[None].astype(np.float32)


class ConditionEnsemble:
    """Loads all Phase-2 condition artefacts; fuses three signals."""

    def __init__(self, models_dir: str):
        self.models_dir = models_dir
        self.available = {"cnn": False, "rf": False, "meta": False}
        self.cnn: Optional[ort.InferenceSession] = None
        self.rf = None
        self.meta = None
        self.meta_feature_order: list = []
        self.cnn_input_size = 96

        cnn_path = os.path.join(models_dir, "condition-cnn.onnx")
        if os.path.exists(cnn_path):
            so = ort.SessionOptions()
            so.intra_op_num_threads = 2
            self.cnn = ort.InferenceSession(cnn_path, sess_options=so, providers=["CPUExecutionProvider"])
            self.cnn_input_size = self.cnn.get_inputs()[0].shape[-1]
            if not isinstance(self.cnn_input_size, int):
                self.cnn_input_size = 96
            self.available["cnn"] = True

        try:
            import joblib
            rf_path = os.path.join(models_dir, "condition-rf.joblib")
            meta_path = os.path.join(models_dir, "condition-meta-lr.joblib")
            if os.path.exists(rf_path):
                self.rf = joblib.load(rf_path)
                self.available["rf"] = True
            if os.path.exists(meta_path):
                self.meta = joblib.load(meta_path)
                # canonical feature order lives in code (META_FEATURES above);
                # feature_names_in_ is informational only
                self.meta_feature_order = list(getattr(self.meta, "feature_names_in_", []))
                self.available["meta"] = True
        except Exception:
            self.rf, self.meta = None, None
            self.available["rf"] = False
            self.available["meta"] = False

    # ------------------------------------------------------------------ #
    def cnn_probs(self, bgr: np.ndarray) -> Optional[np.ndarray]:
        if not self.available["cnn"]:
            return None
        x = _to_cnn_input(bgr, self.cnn_input_size)
        logits = self.cnn.run(None, {self.cnn.get_inputs()[0].name: x})[0]
        e = np.exp(logits[0] - logits[0].max())
        return e / e.sum()

    def rf_probs(self, bgr: np.ndarray) -> Optional[np.ndarray]:
        if not self.available["rf"]:
            return None
        order = getattr(self.rf, "classes_", np.array([0, 1, 2]))
        # CalibratedClassifierCV.predict_proba columns follow classes_ order
        probs = self.rf.predict_proba(feature_vector(bgr).reshape(1, -1))[0]
        full = np.zeros(3, dtype=np.float64)
        for cls_idx, p in zip(order, probs):
            full[int(cls_idx)] = p
        return full

    # ------------------------------------------------------------------ #
    def predict(self, bgr: np.ndarray) -> Dict:
        """Fuse CNN + RF + heuristic into a final condition prediction.

        Fusion = logistic meta-learner over the three soft signals (OOF
        stacking). Falls back to a documented average if the meta-learner is
        unavailable.
        """
        cues = condition_cues(bgr)
        heuristic_signal = None
        try:
            from condition import heuristic_probs
            heuristic_signal = heuristic_probs(cues)
        except Exception:
            heuristic_signal = None

        cnn_p = self.cnn_probs(bgr)
        rf_p = self.rf_probs(bgr)

        if self.available["meta"] and cnn_p is not None and rf_p is not None and heuristic_signal is not None:
            feats = meta_vector(cnn_p, rf_p, heuristic_signal, cues)
            meta_p = self.meta.predict_proba(feats.reshape(1, -1))[0]
            fused = np.zeros(3)
            for cls_idx, p in zip(self.meta.classes_, meta_p):
                fused[int(cls_idx)] = p
            fusion = "meta-logistic"
        else:
            # Honest fallback: average of whichever signals exist
            signals = [p for p in (cnn_p, rf_p, heuristic_signal) if p is not None]
            fused = np.mean(signals, axis=0) if signals else np.array([1 / 3, 1 / 3, 1 / 3])
            fusion = f"mean-fallback({len(signals)}signals)"

        cls_idx = int(np.argmax(fused))
        cls = CONDITION_CLASSES[cls_idx]
        color, label = STATUS_VOCAB[cls]

        # Regions + findings stay pixel-measured (condition.py), scoped by the
        # fused condition class - never invented.
        regions = damage_regions(bgr)
        findings = derive_findings(cues, regions)
        if cls == "clear":
            findings = []
        elif cls == "review":
            findings = findings[:2]

        return {
            "conditionClass": cls,
            "statusColor": color,
            "statusLabel": label,
            # Confidence = the model's visual prediction confidence ONLY.
            "confidence": float(fused[cls_idx]),
            "fusedProbs": [float(p) for p in fused],
            "fusion": fusion,
            "signals": {
                "cnn": None if cnn_p is None else [float(p) for p in cnn_p],
                "rf": None if rf_p is None else [float(p) for p in rf_p],
                "heuristic": None if heuristic_signal is None else [float(p) for p in heuristic_signal],
            },
            "cues": cues,
            "regions": regions,
            "findings": findings,
            "available": dict(self.available),
        }


class OnionVerifier:
    """TensorFlow/Keras-trained binary ONION vs NOT-ONION verifier.

    Second-stage gate on YOLO detections to kill residual false positives.
    Served via ONNX runtime (exported from the Keras SavedModel) to keep the
    serve-time footprint small; training/measurement details in METRICS.md.
    """

    def __init__(self, models_dir: str, threshold: float = 0.5):
        import glob
        candidates = [os.path.join(models_dir, "verifier.onnx")]
        candidates += glob.glob(os.path.join(models_dir, "verifier_savedmodel", "*.onnx"))
        path = next((p for p in candidates if os.path.exists(p)), None)
        self.available = path is not None
        self.threshold = float(threshold)
        self.size = 96
        if path:
            so = ort.SessionOptions()
            so.intra_op_num_threads = 2
            self.sess = ort.InferenceSession(path, sess_options=so, providers=["CPUExecutionProvider"])
            dims = [d for d in self.sess.get_inputs()[0].shape]
            # tf2onnx may keep NHWC (N,96,96,3) or convert to NCHW (N,3,96,96)
            self.layout = "chw" if len(dims) >= 4 and dims[1] == 3 else "hwc"
            size_dim = 2 if self.layout == "chw" else 1
            self.size = dims[size_dim] if isinstance(dims[size_dim], int) else 96
        else:
            self.sess = None

    def _square(self, bgr: np.ndarray) -> np.ndarray:
        h, w = bgr.shape[:2]
        side = max(h, w)
        canvas = np.zeros((side, side, 3), dtype=np.uint8)
        canvas[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = bgr
        return canvas

    def p_onion(self, bgr: np.ndarray) -> Optional[float]:
        if not self.available:
            return None
        img = cv2.resize(self._square(bgr), (self.size, self.size), interpolation=cv2.INTER_AREA)
        # NOTE 1: the Keras model contains a Rescaling(1/255) layer -> feed RAW 0..255
        # NOTE 2: training arrays were OpenCV BGR (never converted) -> keep BGR here
        x = img.astype(np.float32)
        x = x.transpose(2, 0, 1)[None] if self.layout == "chw" else x[None]
        out = self.sess.run(None, {self.sess.get_inputs()[0].name: x})[0]
        return float(out.ravel()[-1])

    def is_onion(self, bgr: np.ndarray):
        """Returns (verdict, p). verdict None => verifier unavailable."""
        p = self.p_onion(bgr)
        if p is None:
            return None, None
        return bool(p >= self.threshold), p
