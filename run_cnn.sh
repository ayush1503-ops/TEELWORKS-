#!/bin/bash
exec > >(tee /home/user/TEELWORKS-/logs/train_cnn.log) 2>&1
cd /home/user/TEELWORKS-/onion-vision-lab/vision-api/train/phase2
CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 train_condition_cnn.py && \
CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 oof_cnn.py
echo "=== CNN_ALL_DONE ==="
