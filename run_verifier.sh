#!/bin/bash
exec > >(tee /home/user/TEELWORKS-/logs/train_verifier.log) 2>&1
cd /home/user/TEELWORKS-/onion-vision-lab/vision-api/train/phase2
CUDA_VISIBLE_DEVICES="" TF_CPP_MIN_LOG_LEVEL=2 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 train_verifier.py
echo "=== VERIFIER_TRAIN_DONE ==="
