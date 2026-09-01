"""PDF report generation with ReportLab (free/pure-Python).

Single-onion report: date/time, image (annotated), onion ID, score breakdown,
grade + rule version, defects with confidence & severity, size estimate,
recommendation, disclaimers.
Batch report: totals, Grade A/B/C/URS percentages, average score, defect tally.
"""
from __future__ import annotations

import base64
import io
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

DISCLAIMERS = [
    "Internal quality (internal rot, sponginess, moisture) cannot be reliably "
    "determined from this image alone.",
    "Grades use the prototype rule set stated above — not an official standard "
    "until an authority specification is configured.",
    "Size is reported in pixels unless a physical size reference is calibrated.",
]

_styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=_styles["Title"], fontSize=17, textColor=colors.HexColor("#7c2d12"))
H2 = ParagraphStyle("H2x", parent=_styles["Heading2"], fontSize=12, textColor=colors.HexColor("#9a3412"))
SMALL = ParagraphStyle("Small", parent=_styles["Normal"], fontSize=8, textColor=colors.HexColor("#6b5546"))


def _b64_to_flowable(b64: str, width=70 * mm):
    try:
        raw = base64.b64decode(b64)
        return Image(io.BytesIO(raw), width=width)  # height auto → aspect kept
    except Exception:
        return Paragraph("(image unavailable)", SMALL)


def _table(data, col_widths=None, header=True) -> Table:
    t = Table(data, colWidths=col_widths)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8c8b8")),
             ("FONTSIZE", (0, 0), (-1, -1), 8.5),
             ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3e5d7")),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def build_analysis_pdf(analysis: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Onion Quality Report {analysis['id']}",
                            topMargin=14 * mm, bottomMargin=14 * mm)
    story = [
        Paragraph("🧅 Onion Quality Assessment Report", H1),
        Paragraph(f"Onion ID: <b>{analysis['id']}</b> · Generated (UTC): {analysis['created_at']}",
                  _styles["Normal"]),
        Spacer(1, 6),
    ]
    if analysis.get("annotated_b64"):
        story += [Paragraph("Analysed image (onion outline, bounding box, defect regions)", SMALL),
                  _b64_to_flowable(analysis["annotated_b64"]), Spacer(1, 8)]

    story.append(Paragraph("Summary", H2))
    grade = analysis.get("grade") or "—"
    story.append(_table([
        ["Quality score", f"{analysis.get('quality_score', '—')}/100" if analysis.get('quality_score') is not None else "—"],
        ["Predicted grade", grade + ("  (prototype rules)" if grade != "UNDETERMINED" else "")],
        ["Rule version", analysis.get("rule_version") or "—"],
        ["Recommendation", analysis.get("recommendation") or "—"],
        ["Model confidence (image evidence)", analysis.get("analysis_confidence")],
        ["Size estimate", f"Ø {analysis.get('diameter_px') or '—'} px (pixel units — see disclaimers)"],
        ["Shape (circularity)", analysis.get("circularity")],
        ["Image", f"{analysis.get('filename','—')} · {analysis.get('format','')} · "
                  f"{analysis.get('img_w','?')}×{analysis.get('img_h','?')} px"],
    ], col_widths=[55 * mm, 105 * mm], header=False))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Score breakdown (transparent scoring)", H2))
    bd = json.loads(analysis.get("breakdown_json") or "{}")
    rows = [["Component", "Points", "Max"]] + [[k, v.get("points"), v.get("max")] for k, v in bd.items()]
    pen = json.loads(analysis.get("defects_penalties_json") or "{}") if analysis.get("defects_penalties_json") else {}
    story.append(_table(rows))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Defect analysis", H2))
    defects = json.loads(analysis.get("defects_json") or "[]")
    rows = [["Defect", "Status", "Confidence", "Severity", "Evidence"]]
    for d in defects:
        rows.append([d.get("label", d.get("name")),
                     d.get("status", "").replace("_", " "),
                     f"{d['confidence']*100:.0f}%" if d.get("confidence") is not None else "—",
                     d.get("severity") or "—",
                     Paragraph(d.get("evidence", "")[:220], SMALL)])
    story.append(_table(rows, col_widths=[28 * mm, 24 * mm, 16 * mm, 16 * mm, 90 * mm]))
    story.append(Spacer(1, 10))

    reasons = json.loads(analysis.get("reasons_json") or "[]")
    if reasons:
        story.append(Paragraph("Why this grade (explainability)", H2))
        story += [Paragraph(f"• {r.get('text','')}", _styles["Normal"]) for r in reasons]
        story.append(Spacer(1, 10))

    story.append(Paragraph("Disclaimers", H2))
    story += [Paragraph("• " + d, SMALL) for d in DISCLAIMER_LIST(analysis)]

    doc.build(story)
    return buf.getvalue()


def DISCLAIMER_LIST(analysis: dict | None = None) -> list[str]:
    base = list(DISCLAIMERS)
    if analysis and analysis.get("rule_version"):
        base[1] = (f"Grades produced by rule set '{analysis['rule_version']}' — prototype "
                   "values, not an official standard until configured from the authority "
                   "specification.")
    return base


def build_batch_pdf(batch: dict, items: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Onion Batch Report {batch['id']}",
                            topMargin=14 * mm, bottomMargin=14 * mm)
    story = [
        Paragraph("🧅 Onion Batch Quality Report", H1),
        Paragraph(f"Batch ID: <b>{batch['id']}</b> · Generated (UTC): {batch['created_at']}", _styles["Normal"]),
        Spacer(1, 8),
        Paragraph("Batch statistics", H2),
        _table([
            ["Total onions analysed", batch.get("total_onions")],
            ["Grade A", f"{batch.get('grade_a_pct', 0):.1f}%"],
            ["Grade B", f"{batch.get('grade_b_pct', 0):.1f}%"],
            ["Grade C", f"{batch.get('grade_c_pct', 0):.1f}%"],
            ["URS / Reject", f"{batch.get('urs_pct', 0):.1f}%"],
            ["Average quality score", batch.get("avg_score")],
        ], col_widths=[60 * mm, 100 * mm], header=False),
        Spacer(1, 8),
        Paragraph("Percentages above are the SHARE OF ONIONS IN THIS BATCH in each grade. "
                  "They are not model confidences.", SMALL),
        Spacer(1, 10),
        Paragraph("Per-onion results", H2),
    ]
    rows = [["#", "Onion ID", "Score", "Grade", "Main defects"]]
    for i, it in enumerate(items, 1):
        rows.append([str(i), it.get("id"), it.get("quality_score") if it.get("quality_score") is not None else "—",
                     it.get("grade", "—"), ", ".join(it.get("defects_detected", [])) or "None detected"])
    story.append(_table(rows, col_widths=[8 * mm, 30 * mm, 14 * mm, 18 * mm, 90 * mm]))
    story += [Spacer(1, 10), Paragraph("Disclaimers", H2)]
    story += [Paragraph("• " + d, SMALL) for d in DISCLAIMER_LIST()]
    doc.build(story)
    return buf.getvalue()
