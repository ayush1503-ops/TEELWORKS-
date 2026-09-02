"""Out-of-fold CNN predictions on the TRAIN condition split (for honest stacking).

Trains the same MobileNetV2 transfer model 3 times (8 epochs, identical recipe
to train_condition_cnn.py), each time holding out one fold of TRAIN CROPS, and
records probabilities for every train image from the fold where its crop was
unseen. These OOF probabilities let the meta-learner fit on ~672 rows instead
of 144 without leakage. CPU-only; logs to stdout (redirect to file).
"""

from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
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
SIZE, BATCH, EPOCHS, NFOLDS = 96, 8, 8, 3
CLASSES = ("clear", "review", "suspect")


class ArrayDataset(Dataset):
    def __init__(self, images_rgb, ys, train):
        base = [transforms.ToPILImage()]
        if train:
            base += [transforms.RandomHorizontalFlip(),
                     transforms.ColorJitter(0.18, 0.18, 0.15),
                     transforms.RandomRotation(9)]
        self.tf = transforms.Compose(base + [
            transforms.Resize((SIZE, SIZE)), transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
        self.images, self.ys = images_rgb, ys

    def __len__(self):
        return len(self.ys)

    def __getitem__(self, i):
        return self.tf(self.images[i]), self.ys[i]


def build_model():
    m = mobilenet_v2(weights=None)
    ckpt = torch.load(PRETRAINED, map_location="cpu", weights_only=False)
    sd = ckpt.get("state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
    m.load_state_dict(sd, strict=False)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 3)
    return m


def main():
    import cv2
    with open(os.path.join(COND_DIR, "labels.json")) as f:
        entries = json.load(f)["splits"]["train"]["entries"]
    imgs = [cv2.cvtColor(cv2.imread(os.path.join(COND_DIR, "train", "images", e["image"])),
                         cv2.COLOR_BGR2RGB) for e in entries]
    ys = np.array([CLASSES.index(e["class"]) for e in entries])
    crops = [e["crop"] for e in entries]

    unique_crops = sorted(set(crops))
    rng = np.random.default_rng(26031)
    crop_fold = {c: int(f) for c, f in zip(unique_crops, rng.permutation(len(unique_crops)) % NFOLDS)}
    fold_of = np.array([crop_fold[c] for c in crops])

    oof = np.full((len(ys), 3), np.nan, dtype=np.float64)
    for k in range(NFOLDS):
        tr_idx = np.where(fold_of != k)[0]
        ho_idx = np.where(fold_of == k)[0]
        print(f"[fold {k}] train crops={len(set(crops[i] for i in tr_idx))} "
              f"holdout crops={len(set(crops[i] for i in ho_idx))} imgs={len(ho_idx)}", flush=True)
        tr = ArrayDataset([imgs[i] for i in tr_idx], ys[tr_idx], train=True)
        ho = ArrayDataset([imgs[i] for i in ho_idx], ys[ho_idx], train=False)
        tr_ld = DataLoader(tr, batch_size=BATCH, shuffle=True, num_workers=0)
        ho_ld = DataLoader(ho, batch_size=BATCH, shuffle=False, num_workers=0)

        torch.manual_seed(26031 + k)
        model = build_model()
        head = [p for n, p in model.named_parameters() if n.startswith("classifier")]
        body = [p for n, p in model.named_parameters() if not n.startswith("classifier")]
        opt = torch.optim.AdamW([{"params": body, "lr": 2e-5}, {"params": head, "lr": 8e-4}],
                                weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
        crit = nn.CrossEntropyLoss(label_smoothing=0.05)
        model.train()
        for ep in range(EPOCHS):
            for x, y in tr_ld:
                opt.zero_grad()
                crit(model(x), y).backward()
                opt.step()
            sched.step()
        model.eval()
        preds = []
        with torch.no_grad():
            for x, _ in ho_ld:
                preds.append(torch.softmax(model(x), 1).numpy())
        oof[ho_idx] = np.concatenate(preds)
        acc = float((oof[ho_idx].argmax(1) == ys[ho_idx]).mean())
        print(f"[fold {k}] holdout acc={acc:.4f}", flush=True)

    assert not np.isnan(oof).any()
    np.save(os.path.join(MODELS_DIR, "phase2", "cnn_oof_train.npy"), oof)
    print("saved cnn OOF (train split) ->", oof.shape)


if __name__ == "__main__":
    main()
