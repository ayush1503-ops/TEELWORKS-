import { jsPDF } from 'jspdf';
import type { AnalyzeResponse } from '../types/vision';

export function buildPdf(response: AnalyzeResponse, imageSrc: string) {
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();
  let y = 48;

  const line = (t: string, size = 10, color = '#3c3550') => {
    doc.setFontSize(size);
    doc.setTextColor(color);
    const parts = doc.splitTextToSize(t, W - 72) as string[];
    for (const p of parts) {
      if (y > H - 40) {
        doc.addPage();
        y = 48;
      }
      doc.text(p, 36, y);
      y += size + 4;
    }
  };

  doc.setFillColor('#0b0714');
  doc.rect(0, 0, W, 84, 'F');
  doc.setTextColor('#ede9fe');
  doc.setFontSize(17);
  doc.text('Onion Vision Lab - visible-condition inspection report', 36, 38);
  doc.setFontSize(9);
  doc.setTextColor('#a78bfa');
  doc.text(
    `SIH PS 26031 prototype · generated ${new Date().toLocaleString()} · engine: ${response.engine}`,
    36,
    58,
  );
  y = 110;

  try {
    const img = new Image();
    img.src = imageSrc;
    if (img.width && img.height) {
      const iw = Math.min(240, W - 72);
      const ih = (img.height / img.width) * iw;
      doc.addImage(imageSrc, 'JPEG', 36, y, iw, Math.min(ih, 200));
      y += Math.min(ih, 200) + 14;
    }
  } catch {
    /* thumbnail optional */
  }

  const counts = { GREEN: 0, YELLOW: 0, RED: 0 };
  response.results.forEach((r) => (counts[r.status] += 1));
  line(`Summary: ${response.results.length} onions - ${counts.GREEN} no obvious visible damage, ${counts.YELLOW} needs review, ${counts.RED} visible damage.`, 11, '#1f1a2e');
  y += 6;

  response.results.forEach((r, i) => {
    if (y > H - 140) {
      doc.addPage();
      y = 48;
    }
    const col = r.status === 'RED' ? '#c0392b' : r.status === 'YELLOW' ? '#b7791f' : '#1e8449';
    doc.setFontSize(11);
    doc.setTextColor(col);
    doc.text(`${i + 1}. ${r.id} - ${r.statusLabel}`, 36, y);
    y += 15;
    line(
      `visual prediction confidence ${(r.confidence * 100).toFixed(0)}% · darkRatio ${r.metrics.darkRatio.toFixed(3)} · satStd ${r.metrics.saturationStd.toFixed(1)} · greenTop ${r.metrics.greenTop.toFixed(3)}`,
      9,
    );
    if (r.findings.length === 0) {
      line('no visible damage cues measured on the visible surface', 9, '#6b6280');
    } else {
      r.findings.forEach((f) => {
        line(`- ${f.kind} (${(f.confidence * 100).toFixed(0)}% evidence): ${f.evidence}`, 9, '#3c3550');
      });
    }
    y += 8;
  });

  y += 6;
  line('Disclaimers', 10, '#1f1a2e');
  (response.meta.disclaimers?.length
    ? response.meta.disclaimers
    : [
        'Analysis is limited to the VISIBLE surface captured in the image.',
        'Internal quality cannot be determined by any camera.',
        'Confidence = visual prediction confidence only, not a food-safety probability.',
      ]
  ).forEach((d) => line(`- ${d}`, 8, '#6b6280'));
  line(
    'Condition labels trained on programmatic synthetic damage over real onion crops from one field photo; field validation pending. See METRICS.md.',
    8,
    '#6b6280',
  );

  const pages = doc.getNumberOfPages();
  for (let p = 1; p <= pages; p++) {
    doc.setPage(p);
    doc.setFontSize(8);
    doc.setTextColor('#9b93b5');
    doc.text(`Onion Vision Lab · prototype report · page ${p}/${pages}`, 36, H - 20);
  }
  doc.save(`onion-vision-report-${Date.now()}.pdf`);
}
