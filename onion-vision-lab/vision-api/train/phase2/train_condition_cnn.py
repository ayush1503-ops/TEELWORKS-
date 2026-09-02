"""Phase-2 PyTorch: per-onion CONDITION classifier via transfer learning.

MobileNetV2 (ImageNet-pretrained; torchvision checkpoint bundled from PyPI
package fdet-offline-mobilenet-weights because download.pytorch.org is
unreachable in this sandbox) -> 3-class head (clear / review / suspect).

Trained on programmatic-synthetic-damage crops (28 train crops), validated on
8 val crops, tested once on the 12 frozen test crops. Exported to ONNX and
served by ensemble.py. CPU-only, batch 8, imgsz 96. Logged to file.
"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import mobilenet_v2

HERE = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, API_DIR)

COND_DIR = os.path.join(API_DIR, "datasets", "condition")
MODELS_DIR = os.path.join(API_DIR, "models")
PRETRAINED = os.path.join(HERE, "pretrained", "mobilenet_v2-b0353104.pth")

SIZE = 96
BATCH = 8
EPOCHS = int(os.environ.get("CNN_EPOCHS", "8"))
CLASSES = ("clear", "review", "suspect")


class CondDataset(Dataset):
    def __init__(self, split: str, train: bool):
        import cv2
        with open(os.path.join(COND_DIR, "labels.json")) as f:
            labels = json.load(f)
        self.entries = labels["splits"][split]["entries"]
        base = [transforms.ToPILImage()]
        if train:
            base += [transforms.RandomHorizontalFlip(),
                     transforms.ColorJitter(0.18, 0.18, 0.15),
                     transforms.RandomRotation(9)]
        self.tf = transforms.Compose(base + [
            transforms.Resize((SIZE, SIZE)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
        self.cv2 = cv2

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, i):
        e = self.entries[i]
        img = self.cv2.imread(os.path.join(COND_DIR, e.get("split", "train"), "images", e["image"]))
        rgb = self.cv2.cvtColor(img, self.cv2.COLOR_BGR2RGB)
        return self.tf(rgb), CLASSES.index(e["class"])


def build_model():
    m = mobilenet_v2(weights=None)
    ckpt = torch.load(PRETRAINED, map_location="cpu", weights_only=False)
    sd = ckpt.get("state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
    m.load_state_dict(sd, strict=False)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 3)
    return m


def run_eval(model, loader, tag, history):
    model.eval()
    correct, total, losses = 0, 0, []
    ys, ps = [], []
    crit = nn.CrossEntropyLoss()
    with torch.no_grad():
        for x, y in loader:
            logits = model(x)
            losses.append(crit(logits, y).item() * len(y))
            pred = logits.argmax(1)
            ys += y.tolist()
            ps += pred.tolist()
            correct += int((pred == y).sum())
            total += len(y)
    from sklearn.metrics import f1_score, confusion_matrix
    acc = correct / max(total, 1)
    f1m = f1_score(ys, ps, average="macro")
    cm = confusion_matrix(ys, ps, labels=[0, 1, 2]).tolist()
    print(f"[{tag}] n={total} acc={acc:.4f} macroF1={f1m:.4f} cm={cm}")
    history.append({"tag": tag, "n": total, "acc": round(acc, 4), "macro_f1": round(float(f1m), 4),
                    "confusion": cm})
    return acc, f1m


def main():
    torch.manual_seed(26031)
    os.makedirs(os.path.join(MODELS_DIR, "phase2"), exist_ok=True)
    train_ds = CondDataset("train", train=True)
    val_ds = CondDataset("val", train=False)
    test_ds = CondDataset("test", train=False)
    for split, ds in (("train", train_ds), ("val", val_ds), ("test", test_ds)):
        for e in ds.entries:
            e["split"] = split
        print(split, len(ds), "images")

    g = torch.Generator().manual_seed(26031)
    train_ld = DataLoader(train_ds, batch_size=BATCH, shuffle=True, num_workers=0, generator=g)
    val_ld = DataLoader(val_ds, batch_size=BATCH, shuffle=False, num_workers=0)
    test_ld = DataLoader(test_ds, batch_size=BATCH, shuffle=False, num_workers=0)

    model = build_model()
    head_params = [p for n, p in model.named_parameters() if n.startswith("classifier")]
    body_params = [p for n, p in model.named_parameters() if not n.startswith("classifier")]
    opt = torch.optim.AdamW([
        {"params": body_params, "lr": 2e-5},
        {"params": head_params, "lr": 8e-4},
    ], weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
    crit = nn.CrossEntropyLoss(label_smoothing=0.05)

    history = []
    best_val, best_state = -1.0, None
    t0 = time.time()
    for ep in range(1, EPOCHS + 1):
        model.train()
        tot_loss, nb = 0.0, 0
        for x, y in train_ld:
            opt.zero_grad()
            loss = crit(model(x), y)
            loss.backward()
            opt.step()
            tot_loss += loss.item()
            nb += 1
        sched.step()
        print(f"epoch {ep}/{EPOCHS} loss={tot_loss / max(nb, 1):.4f} ({time.time() - t0:.0f}s)", flush=True)
        acc, f1m = run_eval(model, val_ld, f"val@{ep}", history)
        if f1m + acc > best_val:
            best_val = f1m + acc
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}

    if best_state:
        model.load_state_dict(best_state)
    test_acc, test_f1 = run_eval(model, test_ld, "TEST", history)

    # persist best weights (so ONNX can be re-exported without retraining)
    torch.save({"state_dict": model.state_dict(), "classes": list(CLASSES), "imgsz": SIZE},
               os.path.join(MODELS_DIR, "phase2", "condition-cnn-state.pt"))

    # ---- export ONNX ----
    onnx_path = os.path.join(MODELS_DIR, "condition-cnn.onnx")
    model.eval()
    dummy = torch.randn(1, 3, SIZE, SIZE)
    torch.onnx.export(model, dummy, onnx_path, opset_version=13,
                      input_names=["input"], output_names=["logits"],
                      dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
                      do_constant_folding=True, dynamo=False)
    print("ONNX exported:", onnx_path)

    # parity check torch vs onnxruntime
    import onnxruntime as ort
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    x = torch.randn(4, 3, SIZE, SIZE)
    with torch.no_grad():
        t_out = torch.softmax(model(x), 1).numpy()
    o_out = sess.run(None, {"input": x.numpy()})[0]
    o_out = np.exp(o_out) / np.exp(o_out).sum(1, keepdims=True)
    parity = float(np.abs(t_out - o_out).max())
    print("torch/onnx parity max diff:", parity)

    out = {
        "framework": "pytorch",
        "model": "MobileNetV2 (ImageNet transfer) + 3-class head",
        "pretrained_source": ("torchvision mobilenet_v2-b0353104 bundled in PyPI package "
                              "fdet-offline-mobilenet-weights (download.pytorch.org unreachable)"),
        "imgsz": SIZE, "batch": BATCH, "epochs": EPOCHS,
        "train_seconds": round(time.time() - t0, 1),
        "test": history[-1], "history": history,
        "onnx_parity_maxdiff": parity,
        "classes": list(CLASSES),
        "scope": ("frozen 12 test crops x 6 variants/class = 216 images, programmatic synthetic "
                  "damage over real crops from ONE field photo; field validation pending"),
    }
    with open(os.path.join(MODELS_DIR, "phase2", "condition-cnn.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: out[k] for k in ("framework", "model", "imgsz", "epochs", "test", "onnx_parity_maxdiff")}, indent=2))


if __name__ == "__main__":
    main()
