"""POST /api/batch — analyse many onion images → grade distribution & URS %.

CRITICAL DISTINCTION (required by the problem statement):
  * distribution percentages = SHARE OF ONIONS IN THIS BATCH per grade
  * per-onion confidences   = how sure the analysis is about ONE onion
These never get mixed; the response says so explicitly in `note`.
"""
import json

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.config import MAX_BATCH_FILES
from app.core.security import enforce_rate_limit
from app.services import database as db
from app.services.analyzer import _disclaimers, analyze_image

DISCLAIMERS = _disclaimers(None)  # batch-level base disclaimers

router = APIRouter(tags=["batch"])

GRADE_KEYS = {"A": "grade_a_pct", "B": "grade_b_pct", "C": "grade_c_pct", "URS": "urs_pct"}


@router.post("/batch", summary="Analyze a batch of onion images → Grade A/B/C/URS %")
async def analyze_batch(request: Request, files: list[UploadFile] = File(...)) -> dict:
    enforce_rate_limit(request.client.host if request.client else "unknown")

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files ({len(files)}). Maximum {MAX_BATCH_FILES} per batch.",
        )
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    items, found_items = [], []
    tally: dict[str, int] = {}

    for idx, f in enumerate(files, 1):
        try:
            result = await analyze_image(f)
            detected = [d["label"] for d in result.get("defects", [])
                        if d.get("status") == "detected"]
            item = {
                "index": idx,
                "filename": f.filename or f"file{idx}",
                "ok": True,
                "analysis_id": result["analysis_id"],
                "found": bool(result["detection"].get("found")),
                "quality_score": (result.get("quality_score") or {}).get("score"),
                "grade": (result.get("grade") or {}).get("grade"),
                "defects_detected": detected,
                "error": None,
            }
            for lbl in detected:
                tally[lbl] = tally.get(lbl, 0) + 1
            if item["found"]:
                found_items.append(item)
        except HTTPException as exc:
            item = {"index": idx, "filename": f.filename or f"file{idx}", "ok": False,
                    "found": False, "analysis_id": None, "quality_score": None,
                    "grade": None, "defects_detected": [],
                    "error": f"HTTP {exc.status_code}: {exc.detail}"}
        items.append(item)

    # ---- grade distribution over the onions that were FOUND ----
    n_found = len(found_items)
    counts = {g: 0 for g in ("A", "B", "C", "URS")}
    for it in found_items:
        counts[it["grade"]] = counts.get(it["grade"], 0) + 1
    distribution = {
        g: {"count": c, "pct": round(100.0 * c / n_found, 1) if n_found else 0.0}
        for g, c in counts.items()
    }
    avg_score = (round(sum(i["quality_score"] for i in found_items) / n_found, 1)
                 if n_found else None)

    batch_id = db.new_id("BATCH")
    row = {
        "id": batch_id,
        "created_at": db.now_iso(),
        "total_onions": n_found,
        "analysed_ok": len([i for i in items if i["ok"]]),
        **{col: distribution[g]["pct"] for g, col in GRADE_KEYS.items()},
        "undetermined": len([i for i in items if i["ok"] and not i["found"]]),
        "avg_score": avg_score,
        "summary_json": json.dumps({"items": items, "tally": tally}),
    }
    db.save_batch(row)

    return {
        "batch_id": batch_id,
        "created_at": row["created_at"],
        "total_files": len(files),
        "analysed_ok": row["analysed_ok"],
        "onions_found": n_found,
        "undetermined": row["undetermined"],
        "distribution": distribution,
        "avg_quality_score": avg_score,
        "defect_tally": tally,
        "items": items,
        "report_url": f"/api/report/batch/{batch_id}.pdf",
        "note": (
            "Grade percentages are the SHARE OF ONIONS IN THIS BATCH in each "
            "grade. They are NOT model confidences — each onion also carries "
            "its own analysis confidence in its individual result."
        ),
        "disclaimers": DISCLAIMERS,
    }
