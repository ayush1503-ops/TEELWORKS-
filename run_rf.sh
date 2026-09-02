#!/bin/bash
exec > >(tee /home/user/TEELWORKS-/logs/train_rf.log) 2>&1
cd /home/user/TEELWORKS-/onion-vision-lab/vision-api/train/phase2
OMP_NUM_THREADS=1 python3 train_rf_meta.py
echo "=== RF_TRAIN_DONE ==="
