# datasets/ — what is kept vs regenerated

KEPT in the repo (small, frozen sources of truth):
- crops/                48 real onion crops + crops_manifest.json (from the ONE field photo)
- scenes/splits.json    crop-level split definition (9 crops held out for the frozen test)
- scenes/frozen_test_manifest.json  the frozen benchmark manifest (170 images)
- scenes/dataset.yaml   ultralytics dataset config
- condition/labels.json frozen condition-split manifest (train/val/test entries + labels)

REGENERATED (gitignored to keep the repo small — every generator is seeded,
so re-running reproduces the exact same images):
    cd train
    python3 make_dataset.py     # scenes/train (520) + scenes/val (130)
    python3 make_dataset2.py    # +400/40 hard negatives + FROZEN scenes/test (170)
    python3 phase2/gen_condition_data.py   # condition/{train,val,test} images
Training run outputs (datasets/runs) are also reproducible via train_yolo.py.
