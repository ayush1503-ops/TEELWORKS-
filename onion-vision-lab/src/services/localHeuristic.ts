/**
 * LOCAL DEMO engine: pure in-browser HSV colour heuristic. No model, no
 * upload - used only as a graceful fallback when the inference API is
 * unreachable, and always labelled DEMO. It runs the same colour logic as the
 * live camera preview (F3) over the whole image and maps the verdicts onto
 * the shared status vocabulary, so the UI stays identical either way.
 */

import type { AnalyzeResponse, FindingKind, OnionResult, SourceMode } from '../types/vision';
import { colorScanFrame } from './liveColorScan';

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export function localHeuristicAnalyze(
  src: HTMLImageElement | HTMLCanvasElement,
  sourceMode: SourceMode,
): AnalyzeResponse {
  const scan = colorScanFrame(src);
  const results: OnionResult[] = scan.blobs.map((b, i) => {
    const darkRatio = Number(b.darkPct.toFixed(4));
    const greenTop = Number(b.sproutPct.toFixed(4));
    const cx = b.x + b.width / 2;
    const cy = b.y + b.height / 2;

    let status: OnionResult['status'];
    let statusLabel: OnionResult['statusLabel'];
    const findings: { kind: FindingKind; confidence: number; evidence: string }[] = [];
    const add = (kind: FindingKind, conf: number, evidence: string) => {
      findings.push({ kind, confidence: Number(Math.min(0.9, conf).toFixed(3)), evidence });
    };

    if (b.verdict === 'FRESH-LOOKING COLORS') {
      status = 'GREEN';
      statusLabel = 'NO OBVIOUS VISIBLE DAMAGE';
    } else if (b.verdict === 'SUSPECT DARK AREAS') {
      status = 'YELLOW';
      statusLabel = 'NEEDS REVIEW';
      if (b.darkPct >= 0.02)
        add('Surface Discoloration', 0.35 + b.darkPct * 2, `darkened pixels ${pct(b.darkPct)} (local colour cue)`);
      if (b.moldPct >= 0.02)
        add('Possible Mold-Like Growth', 0.35 + b.moldPct * 2, `mould-coloured pixels ${pct(b.moldPct)} (local colour cue)`);
      if (b.sproutPct >= 0.02)
        add('Sprouting', 0.35 + b.sproutPct * 2, `green sprout-like colouring ${pct(b.sproutPct)} (local colour cue)`);
    } else {
      status = 'RED';
      statusLabel = 'VISIBLE DAMAGE';
      add('Surface Discoloration', 0.5 + b.darkPct, `dark regions cover ${pct(b.darkPct)} of the detected region (local colour cue)`);
      if (b.moldPct >= 0.03)
        add('Possible Mold-Like Growth', 0.45 + b.moldPct, `mould-like grey/green colouring on ${pct(b.moldPct)} (local colour cue)`);
      if (b.sproutPct >= 0.03) add('Sprouting', 0.5, `green sprout-like colouring on ${pct(b.sproutPct)}`);
      if (findings.length === 0) add('Surface Damage', 0.5, 'strong dark/uneven colour signal on the visible surface (local colour cue)');
    }

    const peak = Math.max(b.darkPct, b.moldPct, b.sproutPct);
    const confidence = Number(Math.min(0.85, Math.max(0.35, 0.3 + peak * 2)).toFixed(3));

    return {
      id: `onion-${i + 1}`,
      bbox: { x: b.x, y: b.y, width: b.width, height: b.height },
      status,
      statusLabel,
      confidence,
      findings,
      regions: status === 'GREEN' ? [] : [{ x: cx, y: cy, r: 0.22 }],
      metrics: {
        darkRatio,
        saturationStd: 0,
        greenTop,
        detectorConfidence: 0.35,
        verifierConfidence: null,
      },
      modelName: 'local-hsv-heuristic-demo',
      variety: b.variety,
      varietyConfidence: Number(b.varietyConfidence.toFixed(3)),
      notes: `LOCAL DEMO · ${b.verdict} — no ML model; rule-based colour cues only`,
    };
  });

  return {
    engine: 'LOCAL DEMO',
    engineDetail:
      'in-browser HSV colour heuristic (no model loaded) — the same on-device logic as the live preview, applied to the full image. Results are illustrative only.',
    imageWidth: (src as HTMLImageElement).naturalWidth || src.width,
    imageHeight: (src as HTMLImageElement).naturalHeight || src.height,
    results,
    meta: {
      sourceMode,
      disclaimers: [
        'LOCAL DEMO MODE: no AI model ran. Results are rule-based colour cues, not model predictions.',
        'Analysis is limited to the VISIBLE surface; internal quality cannot be determined by any camera.',
        'Variety chips are colour ESTIMATES only, never ground truth.',
      ],
    },
  };
}
