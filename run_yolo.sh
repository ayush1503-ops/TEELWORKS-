#!/bin/bash
exec > >(tee /home/user/TEELWORKS-/logs/train_yolo.log) 2>&1
cd /home/user/TEELWORKS-/onion-vision-lab/vision-api/train
YOLO_CONFIG_DIR=/tmp OMP_NUM_THREADS=2 python3 train_yolo.py
echo "=== YOLO_TRAIN_DONE ==="
