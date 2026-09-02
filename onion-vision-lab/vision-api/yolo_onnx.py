"""ONNX YOLOv8n single-class ('onion') detector - serving wrapper.

Self-contained letterbox preprocess + numpy postprocess (no ultralytics needed
at serve time). Runs on onnxruntime CPU.

Serving configuration: conf 0.45, letterbox 320 px (train-matched; see
METRICS.md for the measured serving-size selection - 832 was Phase-1's
config for a differently-trained model and measurably degrades this one).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import cv2
import numpy as np
import onnxruntime as ort

CONF_THRESHOLD = 0.45
IOU_THRESHOLD = 0.55
# Serving letterbox size. The model was trained (from scratch) at imgsz 320,
# and serving-size selection on the VAL split measured:
#   320: P 1.000 R 0.947 F1 0.973 | 640: F1 0.728 | 832: F1 0.308 (scale mismatch)
# so 320 is used - the Phase-1 "832px" config belonged to a different training
# run and is deliberately NOT reused here (measured, see METRICS.md).
INPUT_SIZE = 320
CLASS_NAME = "onion"  # single trained class


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


def letterbox(img: np.ndarray, size: int = INPUT_SIZE) -> tuple:
    h, w = img.shape[:2]
    scale = size / max(h, w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    canvas[top: top + nh, left: left + nw] = resized
    return canvas, scale, left, top


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> List[int]:
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= iou_thr]
    return keep


class OnionDetector:
    def __init__(self, onnx_path: str, conf: float = CONF_THRESHOLD, input_size: int = INPUT_SIZE):
        so = ort.SessionOptions()
        so.intra_op_num_threads = 2
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(onnx_path, sess_options=so, providers=["CPUExecutionProvider"])
        self.input_name = self.sess.get_inputs()[0].name
        self.conf = conf
        self.input_size = input_size

    def detect(self, bgr: np.ndarray, max_det: int = 64) -> List[Detection]:
        canvas, scale, left, top = letterbox(bgr, self.input_size)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = rgb.astype(np.float32) / 255.0
        tensor = tensor.transpose(2, 0, 1)[None]  # 1x3xSxS
        out = self.sess.run(None, {self.input_name: tensor})[0]

        # YOLOv8 export layout: (1, 4+nc, N) -> (5, N) for single class
        pred = np.squeeze(out, 0)
        if pred.shape[0] != 5:  # (N, 5) transposed layout
            pred = pred.T
        boxes_cxcywh, confs = pred[:4, :], pred[4, :]

        mask = confs >= self.conf
        if not mask.any():
            return []
        boxes_cxcywh = boxes_cxcywh[:, mask].T
        confs = confs[mask]

        # cxcywh -> xy1xy2 in letterbox space, then undo letterbox
        xy = np.zeros((confs.shape[0], 4), dtype=np.float32)
        xy[:, 0] = boxes_cxcywh[:, 0] - boxes_cxcywh[:, 2] / 2 - left
        xy[:, 1] = boxes_cxcywh[:, 1] - boxes_cxcywh[:, 3] / 2 - top
        xy[:, 2] = boxes_cxcywh[:, 0] + boxes_cxcywh[:, 2] / 2 - left
        xy[:, 3] = boxes_cxcywh[:, 1] + boxes_cxcywh[:, 3] / 2 - top
        xy /= scale
        h, w = bgr.shape[:2]
        xy[:, [0, 2]] = np.clip(xy[:, [0, 2]], 0, w - 1)
        xy[:, [1, 3]] = np.clip(xy[:, [1, 3]], 0, h - 1)

        keep = _nms(xy, confs, IOU_THRESHOLD)
        keep = keep[:max_det]
        dets = [Detection(float(xy[i, 0]), float(xy[i, 1]), float(xy[i, 2]), float(xy[i, 3]), float(confs[i]))
                for i in keep]
        dets.sort(key=lambda d: -d.conf)
        return dets


def crop_detection(bgr: np.ndarray, det: Detection, pad: float = 0.10) -> np.ndarray:
    """Crop a detection box with context padding, clamped to the image."""
    h, w = bgr.shape[:2]
    pw, ph = det.width * pad, det.height * pad
    x1 = int(max(0, det.x1 - pw))
    y1 = int(max(0, det.y1 - ph))
    x2 = int(min(w - 1, det.x2 + pw))
    y2 = int(min(h - 1, det.y2 + ph))
    if x2 - x1 < 8 or y2 - y1 < 8:
        x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
    return bgr[y1:y2, x1:x2]
