/**
 * LOCAL DEMO engine: pure in-browser HSV heuristic. No model, no upload -
 * used only as a graceful fallback when the inference API is unreachable, and
 * always labelled DEMO. It segments saturated blob regions (any produce-like
 * colour) and derives the same cue metrics as the API's Phase-1 heuristic.
 */

import type { AnalyzeResponse, OnionResult, SourceMode } from '../types/vision';

const MAX_SIDE = 640;

function toImageData(src: HTMLImageElement | HTMLCanvasElement): ImageData {
  const w = (src as HTMLImageElement).naturalWidth || src.width;
  const h = (src as HTMLImageElement).naturalHeight || src.height;
  const scale = Math.min(1, MAX_SIDE / Math.max(w, h));
  const cw = Math.max(32, Math.round(w * scale));
  const ch = Math.max(32, Math.round(h * scale));
  const c = document.createElement('canvas');
  c.width = cw;
  c.height = ch;
  const ctx = c.getContext('2d');
  if (!ctx) throw new Error('canvas unavailable');
  ctx.drawImage(src, 0, 0, cw, ch);
  return ctx.getImageData(0, 0, cw, ch);
}

interface Blob {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  n: number;
  dark: number;
  greenTop: number;
  satSum: number;
  satSq: number;
}

/** connected components over "saturated, mid-bright" pixels (grid downsampled) */
function findBlobs(d: ImageData): Blob[] {
  const { width: W, height: H, data } = d;
  const label = new Int32Array(W * H).fill(0);
  const blobs: Blob[] = [];
  const isFruit = (i: number) => {
    const r = data[i * 4], g = data[i * 4 + 1], b = data[i * 4 + 2];
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const v = max, s = max === 0 ? 0 : (max - min) / max;
    return s > 0.25 && v > 60 && v < 245;
  };
  let next = 1;
  const stack: number[] = [];
  for (let start = 0; start < W * H; start++) {
    if (label[start] !== 0 || !isFruit(start)) continue;
    const id = next++;
    stack.push(start);
    label[start] = id;
    const blob: Blob = { x0: W, y0: H, x1: 0, y1: 0, n: 0, dark: 0, greenTop: 0, satSum: 0, satSq: 0 };
    while (stack.length) {
      const p = stack.pop() as number;
      const x = p % W, y = (p / W) | 0;
      blob.n++;
      blob.x0 = Math.min(blob.x0, x);
      blob.y0 = Math.min(blob.y0, y);
      blob.x1 = Math.max(blob.x1, x);
      blob.y1 = Math.max(blob.y1, y);
      const r = data[p * 4], g = data[p * 4 + 1], b = data[p * 4 + 2];
      const max = Math.max(r, g, b), min = Math.min(r, g, b);
      const v = max, s = max === 0 ? 0 : (max - min) / max;
      if (v < 90 && s > 0.15) blob.dark++;
      if (y < blob.y0 + (blob.y1 - blob.y0) * 0.3 && g > r * 1.1 && g > b * 1.1) blob.greenTop++;
      blob.satSum += s;
      blob.satSq += s * s;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
        const q = ny * W + nx;
        if (label[q] === 0 && isFruit(q)) {
          label[q] = id;
          stack.push(q);
        }
      }
    }
    if (blob.n > 250) blobs.push(blob);
  }
  return blobs.sort((a, b) => b.n - a.n).slice(0, 12);
}

export function localHeuristicAnalyze(
  src: HTMLImageElement | HTMLCanvasElement,
  sourceMode: SourceMode,
): AnalyzeResponse {
  const d = toImageData(src);
  const results: OnionResult[] = findBlobs(d).map((b, i) => {
    const darkRatio = b.dark / b.n;
    const greenTop = b.greenTop / Math.max(1, b.n * 0.25);
    const satMean = b.satSum / b.n;
    const satStd = Math.sqrt(Math.max(0, b.satSq / b.n - satMean * satMean));
    let status: OnionResult['status'] = 'GREEN';
    let statusLabel: OnionResult['statusLabel'] = 'NO OBVIOUS VISIBLE DAMAGE';
    const findings: OnionResult['findings'] = [];
    if (darkRatio > 0.115) {
      status = 'RED';
      statusLabel = 'VISIBLE DAMAGE';
      findings.push({
        kind: 'Surface Discoloration',
        confidence: Math.min(0.9, 0.5 + darkRatio),
        evidence: `dark regions cover ${(darkRatio * 100).toFixed(1)}% of the detected region (local heuristic cue)`,
      });
    } else if (darkRatio > 0.045 || greenTop > 0.16 || satStd > 0.16) {
      status = 'YELLOW';
      statusLabel = 'NEEDS REVIEW';
      if (greenTop > 0.16)
        findings.push({
          kind: 'Sprouting',
          confidence: Math.min(0.85, 0.4 + greenTop),
          evidence: `green shoot-like colouring in the upper region (greenTop ${(greenTop * 100).toFixed(1)}%)`,
        });
      if (darkRatio > 0.045)
        findings.push({
          kind: 'Surface Discoloration',
          confidence: Math.min(0.8, 0.4 + darkRatio * 2),
          evidence: `darkened pixels ${(darkRatio * 100).toFixed(1)}% (local heuristic cue)`,
        });
    }
    void statusLabel;
    return {
      id: `onion-${i + 1}`,
      bbox: {
        x: b.x0 / d.width,
        y: b.y0 / d.height,
        width: (b.x1 - b.x0) / d.width,
        height: (b.y1 - b.y0) / d.height,
      },
      status,
      statusLabel,
      confidence: 0.35,
      findings,
      regions: status === 'GREEN' ? [] : [{ x: 0.5, y: 0.55, r: 0.25 }],
      metrics: {
        darkRatio: Number(darkRatio.toFixed(4)),
        saturationStd: Number((satStd * 255).toFixed(2)),
        greenTop: Number(greenTop.toFixed(4)),
        detectorConfidence: 0.35,
      },
      modelName: 'local-hsv-heuristic-demo',
      notes: 'LOCAL DEMO - no ML model; rule-based colour cues only',
    };
  });
  return {
    engine: 'LOCAL DEMO',
    engineDetail: 'in-browser HSV heuristic (no model loaded) - results are illustrative only',
    imageWidth: (src as HTMLImageElement).naturalWidth || src.width,
    imageHeight: (src as HTMLImageElement).naturalHeight || src.height,
    results,
    meta: {
      sourceMode,
      disclaimers: [
        'LOCAL DEMO MODE: no AI model ran. Results are rule-based colour cues, not model predictions.',
        'Analysis is limited to the VISIBLE surface; internal quality cannot be determined by any camera.',
      ],
    },
  };
}
