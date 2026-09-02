#!/bin/bash
# serve the vision API on :8788
cd "$(dirname "$0")"
exec python3 -m uvicorn app:app --host 0.0.0.0 --port 8788
