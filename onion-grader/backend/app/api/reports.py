"""Report endpoints — PDF generation + recent analyses."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services import database as db
from app.services.report import build_analysis_pdf, build_batch_pdf

router = APIRouter(tags=["reports"])


@router.get("/report/{analysis_id}.pdf", summary="Download the PDF report for one analysis")
def analysis_pdf(analysis_id: str):
    row = db.get_analysis(analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    # attach penalties json kept inside breakdown_json
    row["defects_penalties_json"] = None
    pdf = build_analysis_pdf(row)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="onion-report-{analysis_id}.pdf"'})


@router.get("/report/batch/{batch_id}.pdf", summary="Download the PDF batch report")
def batch_pdf(batch_id: str):
    row = db.get_batch(batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found.")
    import json
    summary = json.loads(row.get("summary_json") or "{}")
    pdf = build_batch_pdf(row, summary.get("items", []))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="batch-report-{batch_id}.pdf"'})


@router.get("/report/scan/{scan_id}.pdf", summary="Download the PDF report of a pile scan")
def scan_pdf(scan_id: str):
    row = db.get_batch(scan_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found.")
    import json
    summary = json.loads(row.get("summary_json") or "{}")
    pdf = build_batch_pdf(row, summary.get("items", []))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="scan-report-{scan_id}.pdf"'})


@router.get("/analyses/recent", summary="Recent analyses (no images, facts only)")
def recent(limit: int = 10):
    limit = max(1, min(limit, 50))
    return {"analyses": db.recent_analyses(limit)}
