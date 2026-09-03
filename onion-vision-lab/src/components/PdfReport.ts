/**
 * F7 — formal, mandi/QC-lab-style PDF report. Black on white, plain fonts,
 * header rules, numbered sections. No gradients, no emoji, no "AI styling".
 *
 * buildPdf(response, imageSrc[, opts]) saves:
 *   ONION QUALITY INSPECTION REPORT
 *   report number OVL/<date>/<serial> · date & time · place/line ·
 *   inspector name & signature · sample info · summary · specimen
 *   photograph · per-onion observations table · scope & disclaimers ·
 *   ANNEXURE A (full limitations).
 */

import { jsPDF } from 'jspdf';
import type { AnalyzeResponse } from '../types/vision';
import { VARIETY_LABEL } from '../types/vision';

interface PdfOptions {
  place?: string;
  inspector?: string;
}

function reportNumber(): string {
  const d = new Date();
  const ymd = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
  const serial = String(Math.floor(Math.random() * 900) + 100);
  return `OVL/${ymd}/${serial}`;
}

function fmtDateTime(d: Date): string {
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function buildPdf(response: AnalyzeResponse, imageSrc: string, opts: PdfOptions = {}) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  const M = 46; // margin
  const CW = W - M * 2;
  let y = 0;
  const no = reportNumber();

  const ensure = (need: number) => {
    if (y + need > H - 52) {
      doc.addPage();
      y = 40;
      return true;
    }
    return false;
  };

  const text = (t: string, size = 10, x = M, style: 'normal' | 'bold' | 'italic' = 'normal', color: [number, number, number] = [20, 20, 20]) => {
    doc.setFont('helvetica', style);
    doc.setFontSize(size);
    doc.setTextColor(color[0], color[1], color[2]);
    doc.text(t, x, y);
  };

  const para = (t: string, size = 9.5, leading = 12.5) => {
    const parts = doc.splitTextToSize(t, CW) as string[];
    for (const p of parts) {
      ensure(leading);
      text(p, size);
      y += leading;
    }
  };

  const rule = (thick = 1) => {
    ensure(6);
    y += 4;
    doc.setDrawColor(20);
    doc.setLineWidth(thick);
    doc.line(M, y, W - M, y);
    y += thick + 3;
  };

  const heading = (num: string, title: string) => {
    ensure(30);
    y += 10;
    doc.setFillColor(230, 230, 230);
    doc.rect(M, y - 8, CW, 16, 'F');
    text(`${num}  ${title}`, 10.5, M + 6, 'bold');
    y += 16;
  };

  const fieldLine = (label: string, value: string, width = CW / 2 - 6) => {
    const parts = doc.splitTextToSize(value || '.', width) as string[];
    text(label, 8.5, M, 'bold', [90, 90, 90]);
    const vh = parts.length * 11;
    ensure(vh + 4);
    y += 12;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.5);
    doc.setTextColor(20);
    doc.text(parts, M + label.length * 4.3 + 6, y - 2);
    // underline space for hand-filling
    if (!value) {
      doc.setDrawColor(160);
      doc.setLineWidth(0.5);
      doc.line(M, y + 3, M + width, y + 3);
    }
    y += 6;
  };

  /* ---------------- header ---------------- */
  y = 42;
  text('SMART ONION PROJECT · SIH PS 26031 · CAMERA-BASED INSPECTION TOOL', 7.5, M, 'normal', [110, 110, 110]);
  text('ONION QUALITY INSPECTION REPORT', 19, M, 'bold');
  y += 24;
  text('Camera-based visible-surface inspection of onion skin — findings limited to the five allowed observations.', 9.5, M);
  y += 16;
  doc.setDrawColor(20);
  doc.setLineWidth(2);
  doc.line(M, y, W - M, y);
  y += 3;
  doc.setLineWidth(0.5);
  doc.line(M, y, W - M, y);
  y += 14;

  /* ---------------- meta fields ---------------- */
  const now = new Date();
  fieldLine('Report No.', no, 180);
  fieldLine('Date & Time', fmtDateTime(now), 180);
  fieldLine('Place / Market yard / Line', opts.place ?? '', 220);
  fieldLine('Inspector name', opts.inspector ?? '', 220);
  y += 2;
  fieldLine('Mode of capture', response.meta.sourceMode === 'camera' ? 'Live camera capture' : response.meta.sourceMode === 'demo' ? 'Sample photo' : 'Uploaded photo', 180);
  text('Signature ______________________', 9.5, W - M - 210);
  y += 18;
  rule(0.5);

  /* ---------------- 1. sample info ---------------- */
  heading('1.', 'SAMPLE INFORMATION');
  const counts = { GREEN: 0, YELLOW: 0, RED: 0 } as Record<string, number>;
  response.results.forEach((r) => (counts[r.status] += 1));
  para(`Specimen: one still photograph (${response.imageWidth} × ${response.imageHeight} px). Onions analysed: ${response.results.length} (${counts.GREEN} no obvious visible damage, ${counts.YELLOW} needs review, ${counts.RED} visible damage). Analysis engine: ${response.engine} — ${response.engineDetail}. ${response.meta.fusion ? `Fusion used: ${response.meta.fusion}.` : ''}`);
  y += 4;

  /* ---------------- 2. summary ---------------- */
  heading('2.', 'SUMMARY OF FINDINGS');
  if (response.results.length === 0) {
    para('No onions were detected in this image. Nothing is inferred from absence; re-photograph closer or with better light and re-submit.');
  } else {
    const r = response.results;
    const bad = r.filter((x) => x.status === 'RED').length;
    const mid = r.filter((x) => x.status === 'YELLOW').length;
    para(
      `Of ${r.length} onion${r.length === 1 ? '' : 's'} inspected from the visible surface only: ${counts.GREEN} showed no obvious visible damage, ${mid} need${mid === 1 ? 's' : ''} review, and ${bad} showed clear visible damage. ` +
        `Confidence figures quoted per onion are visual prediction confidences of the models — they are NOT food-safety probabilities. A camera cannot determine internal quality; manual cutting remains the only check for internal defects such as black mold or hollow heart.`,
    );
  }
  y += 4;

  /* ---------------- 3. specimen photo ---------------- */
  heading('3.', 'SPECIMEN PHOTOGRAPH');
  try {
    const img = new Image();
    img.src = imageSrc;
    const iw = Math.min(280, CW);
    const ih = (img.height / Math.max(1, img.width)) * iw;
    const ihh = Math.min(ih, 240);
    if (img.width > 0) {
      ensure(ihh + 20);
      doc.addImage(imageSrc, 'JPEG', W / 2 - iw / 2, y, iw, ihh);
      y += ihh + 10;
      text('Specimen 1 — photograph as received (single frame).', 8, W / 2 - iw / 2, 'italic', [90, 90, 90]);
      y += 12;
    }
  } catch {
    /* image embed optional */
  }
  rule(0.5);

  /* ---------------- 4. per-onion table ---------------- */
  heading('4.', 'PER-ONION OBSERVATIONS');
  const cols = [
    { title: '#', w: 22 },
    { title: 'ID', w: 62 },
    { title: 'Variety (est.)', w: 92 },
    { title: 'Status', w: 78 },
    { title: 'Vis. conf.', w: 46 },
    { title: 'Findings (vocabulary only)', w: CW - 22 - 62 - 92 - 78 - 46 },
  ];
  const drawHeader = () => {
    doc.setFillColor(235, 235, 235);
    doc.rect(M, y - 9, CW, 16, 'F');
    doc.setDrawColor(20);
    doc.setLineWidth(0.5);
    doc.line(M, y + 7, W - M, y + 7);
    let x = M;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    for (const c of cols) {
      doc.text(c.title, x + 3, y);
      x += c.w;
    }
    y += 13;
  };
  drawHeader();
  response.results.forEach((r, i) => {
    const findingsTxt =
      r.findings.length === 0
        ? 'none on visible surface'
        : r.findings
            .map((f) => `${f.kind} (${(f.confidence * 100).toFixed(0)}%)`)
            .join('; ');
    const rows = doc.splitTextToSize(findingsTxt, cols[5].w - 6) as string[];
    const rowH = Math.max(13, rows.length * 10 + 6);
    if (ensure(rowH + 30)) drawHeader();
    doc.setFontSize(8.5);
    doc.setFont('helvetica', 'normal');
    let x = M;
    const y0 = y - 3;
    doc.text(String(i + 1), x + 3, y0 + 5);
    x += cols[0].w;
    doc.text(r.id, x + 3, y0 + 5);
    x += cols[1].w;
    doc.text(VARIETY_LABEL[r.variety], x + 3, y0 + 5);
    x += cols[2].w;
    doc.setFont('helvetica', 'bold');
    doc.text(
      r.status === 'GREEN' ? 'GREEN' : r.status === 'YELLOW' ? 'YELLOW' : 'RED',
      x + 3,
      y0 + 5,
    );
    doc.setFont('helvetica', 'normal');
    x += cols[3].w;
    doc.text(`${(r.confidence * 100).toFixed(0)}%`, x + 3, y0 + 5);
    x += cols[4].w;
    doc.text(rows as string[], x + 3, y0 + 5);
    // row bottom line
    doc.setDrawColor(210);
    doc.setLineWidth(0.4);
    doc.line(M, y0 + rowH - 4, W - M, y0 + rowH - 4);
    y = y0 + rowH;
  });
  y += 8;
  text('Status vocabulary — GREEN: NO OBVIOUS VISIBLE DAMAGE · YELLOW: NEEDS REVIEW · RED: VISIBLE DAMAGE. Variety is a colour-family ESTIMATE from the visible skin, not ground truth.', 7.5, M, 'italic', [80, 80, 80]);
  y += 10;

  /* ---------------- 5. scope & disclaimers ---------------- */
  heading('5.', 'SCOPE & DISCLAIMERS');
  const disclaimers = response.meta.disclaimers?.length
    ? response.meta.disclaimers
    : [
        'Analysis is limited to the VISIBLE surface captured in the image.',
        'Internal quality cannot be determined by any camera.',
        'Confidence = visual prediction confidence only, not a food-safety probability.',
      ];
  disclaimers.forEach((d, i) => para(`${i + 1}. ${d}`, 8.5, 11.5));
  para('Every measured number in this tool is reported with its scope in METRICS.md: model outputs derive from one field photo and programmatic synthetic benchmarks — field validation is pending.', 8.5, 11.5);

  /* ---------------- annexure A ---------------- */
  if (ensure(80)) y += 6;
  y += 16;
  rule(1.4);
  y += 4;
  text('ANNEXURE A — FULL LIMITATIONS (technical / model / deployment)', 10, M, 'bold');
  rule(0.5);
  const annex: Array<[string, string]> = [
    ['A1', 'External defects only. The camera cannot detect inside black mold or hollow heart — internal quality cannot be determined by any camera.'],
    ['A2', 'Lighting dependent. Best in daylight; low-light mandi/godown performance is expected to drop but is NOT yet measured — no number is invented for it.'],
    ['A3', 'Single training variety. A colour-shift stress test is measured and tabulated in METRICS.md; shallots and other alliums are not yet measured.'],
    ['A4', 'Overlapping piles. Occluded onions are invisible to the camera; only visible onions are counted (pile counting is not yet measured).'],
    ['B1', 'Limited dataset. True counts: 48 real crops from one field photo, expanded with seeded synthetic scenes — versus the industry-scale 50k+ multi-soil / season / size datasets.'],
    ['B2', 'No shelf-life prediction. The tool cannot predict rot in 3 days vs 30 days.'],
    ['B3', 'No weight and no exact millimetre size grading.'],
    ['C1', 'Serverless free tiers time out near ~10 s. The full pipeline measures ~3–4 s per photo on 2 vCPUs — serve on a CPU container, not serverless; 3+ batch uploads can time out.'],
    ['C2', 'No GPU on free tiers. Mitigated by compact (~30 MB) ONNX serving — no 150–300 MB PyTorch/TF runtime in production.'],
    ['C3', 'No offline full-AI. The browser keeps only the clearly-labelled colour heuristic for offline use.'],
  ];
  annex.forEach(([code, t]) => para(`${code}. ${t}`, 8.3, 11));
  y += 6;

  /* ---------------- footer every page ---------------- */
  const pages = doc.getNumberOfPages();
  for (let p = 1; p <= pages; p++) {
    doc.setPage(p);
    doc.setDrawColor(200);
    doc.setLineWidth(0.4);
    doc.line(M, H - 30, W - M, H - 30);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(120);
    doc.text(`OVL — Onion Vision Lab · ${no}`, M, H - 18);
    doc.text(`Page ${p} / ${pages}`, W - M, H - 18, { align: 'right' });
  }

  doc.save(`onion-quality-inspection-${Date.now()}.pdf`);
}
