# Phase Tracker

| # | Phase | Deliverable | Status | Notes |
|---|---|---|---|---|
| 1 | Image input | Camera + upload UI, preview, validating API | ✅ Done | security tests pass |
| 2 | OpenCV pipeline | Segmentation (3 candidate masks), morphology, contours, measurements | ✅ Done | circular hue stats for red onions |
| 3 | Rule-based analysis | 6 evidence defects + 2 insufficient-evidence cases, transparent score | ✅ Done | confidences computed, never invented |
| 4 | Dataset | Verified public options (261-img rot/sprout set) + collection guide + builder script | ✅ guide / ⬜ collection | docs/DATASET.md |
| 5 | ML training | RandomForest trained on synthetic-v1 (630 imgs, 7 classes, 97.8% val acc — synthetic only) | ✅ synthetic bootstrap / ⬜ field data | scripts/generate_synthetic_dataset.py |
| 6 | Model integration | Auto-detect models/classifier.pkl, blends ML probabilities | ✅ Done | honest flag trained_ml_loaded |
| 7 | Client ↔ API | Single-origin web app; API reusable by RN/Flutter | ✅ Done | |
| 8 | Grading engine | config/grading_rules.yaml → A/B/C/URS + recommendation + rule_version stamp | ✅ Done | YAML edit changes grades (tested) |
| 9 | Batch & URS | ≤25 images → distribution %, avg score, defect tally, batch PDF | ✅ Done | share-of-batch ≠ confidence (stated) |
| 10 | PDF reports | Single + batch PDFs with breakdown, defects, disclaimers | ✅ Done | ReportLab |
| 11 | Database | SQLite: analyses / batch_runs / eval_results; no personal data | ✅ Done | Supabase-ready schema |
| 12 | Explainability | Annotated image + score breakdown + reasons + rule version | ✅ Done | Grad-CAM unlocked at Phase 5 |
| 13 | Evaluation | Test page: actual vs predicted + accuracy/P/R/F1/confusion | ✅ Done | metrics only from real uploads |
| 14 | Deployment | Render/Railway/Fly guide + Dockerfile + hardening checklist | ✅ Done | docs/DEPLOYMENT.md |

## Remaining human work (cannot be done in code)

1. **Collect the dataset** (Phase 4 field work) — guide: `docs/DATASET.md`
2. **Train the model** on it — `scripts/build_dataset.py` → `scripts/train_baseline.py`
3. **Enter official grading rules** when the authority supplies them — edit `config/grading_rules.yaml`, set `official_standard: true`
4. Optional: mm calibration (coin/ArUco reference) and YOLO multi-onion model via Colab
