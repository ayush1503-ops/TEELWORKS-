/**
 * LIVE COLOUR HEURISTIC (F3) — runs ENTIRELY in the browser, on-device.
 *
 * While the camera is only POINTING (no photo click yet), this module samples
 * a ~320px frame about once every 1.2 s and, from COLOURS ALONE (HSV), draws
 * boxes around onion-like blobs and says whether each one *looks* rotten:
 *
 *   "FRESH-LOOKING COLORS" / "SUSPECT DARK AREAS" / "STRONG DARK/SPORE COLORS"
 *
 * with dark-patch %, mould-colour % and sprout %. It also gives a per-onion
 * VARIETY ESTIMATE (red/golden/purple/white/cream) - an estimate, never ground
 * truth. Frames are kept in memory only.
 *
 * Honesty labels that must accompany it in the UI:
 *   "colour heuristic — not the AI model; capture for the full verdict"
 *
 * Thresholds (spec, hue in degrees, s/v in 0..1):
 *   red    h<=22|h>=350 s>=0.25 v>=0.16
 *   golden 22-48        s>=0.28 v>=0.25
 *   purple 285-350      s>=0.14 v>=0.18
 *   cream  s<0.26 v>=0.55 (warm hue)
 *   dark   v<0.22
 *   moldish  h55-170 s0.06-0.42 v0.18-0.62
 *   sprout   h55-170 s>0.3    v>0.3
 */

import type { OnionVariety } from '../types/vision';

export type LiveVerdict = 'FRESH-LOOKING COLORS' | 'SUSPECT DARK AREAS' | 'STRONG DARK/SPORE COLORS';

export const VERDICT_TEXT: Record<LiveVerdict, string> = {
  'FRESH-LOOKING COLORS': 'FRESH-LOOKING COLORS',
  'SUSPECT DARK AREAS': 'SUSPECT DARK AREAS',
  'STRONG DARK/SPORE COLORS': 'STRONG DARK/SPORE COLORS',
};

export interface LiveBlob {
  /** normalized 0..1 box inside the sampled frame */
  x: number;
  y: number;
  width: number;
  height: number;
  verdict: LiveVerdict;
  darkPct: number; // % of blob pixels that are dark
  moldPct: number; // % grey-green mould-like
  sproutPct: number; // % green sprout-like
  variety: OnionVariety;
  varietyConfidence: number;
  pixelCount: number;
}

export interface ColorScanResult {
  blobs: LiveBlob[];
  sampledAt: number;
  frameWidth: number;
  frameHeight: number;
  frameMs: number;
}

const MAX_SIDE = 320;
const GRID = 6; // 6px-grid connected components (~1 frame/1.2s on low-end phones)

/* colour classes per pixel (returned as a bitmask value) */
const C_RED = 1;
const C_GOLD = 2;
const C_PURPLE = 4;
const C_CREAM = 8;
const C_SKIN = C_RED | C_GOLD | C_PURPLE | C_CREAM;
const C_DARK = 16;
const C_MOLD = 32;
const C_SPROUT = 64;

function classify(h: number, s: number, v: number): number {
  let c = 0;
  if ((h <= 22 || h >= 350) && s >= 0.25 && v >= 0.16) c |= C_RED;
  else if (h > 22 && h <= 48 && s >= 0.28 && v >= 0.25) c |= C_GOLD;
  else if (h > 285 && h < 350 && s >= 0.14 && v >= 0.18) c |= C_PURPLE;
  if (s < 0.26 && v >= 0.55 && (h <= 60 || h >= 300)) c |= C_CREAM;
  if (v < 0.22) c |= C_DARK;
  if (h >= 55 && h <= 170 && s > 0.06 && s < 0.42 && v >= 0.18 && v <= 0.62) c |= C_MOLD;
  if (h >= 55 && h <= 170 && s > 0.3 && v > 0.3) c |= C_SPROUT;
  return c;
}

interface GridBlob {
  n: number;
  dark: number;
  mold: number;
  sprout: number;
  // variety accumulators over skin pixels (hue hist of 18 bins x 20 deg + counts)
  skinN: number;
  skinWarmCream: number;
  hueHist: Int32Array; // 18 bins
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

function varietyFromBlob(b: GridBlob): { variety: OnionVariety; confidence: number } {
  if (b.skinN < 12) return { variety: 'UNKNOWN', confidence: 0 };
  // cream-dominant bright surface -> white/cream (low-sat hue is unstable)
  const creamFrac = b.skinWarmCream / b.skinN;
  const chromatic = b.skinN - b.skinWarmCream;
  if (creamFrac >= 0.25 && chromatic < b.skinWarmCream) {
    return { variety: 'WHITE', confidence: 1 };
  }
  // weighted median hue from the histogram
  let cum = 0;
  const half = b.skinN / 2;
  let medBin = 0;
  for (let i = 0; i < 18; i++) {
    cum += b.hueHist[i];
    if (cum >= half) {
      medBin = i;
      break;
    }
  }
  const hue = medBin * 20 + 10; // bin centre in degrees
  if (hue <= 24 || hue >= 345) return { variety: 'RED', confidence: 0.8 };
  if (hue <= 48) return { variety: 'GOLDEN', confidence: 0.8 };
  if (hue >= 190 && hue < 345) return { variety: 'PURPLE', confidence: 0.8 };
  return { variety: 'UNKNOWN', confidence: 0 };
}

function verdictOf(darkPct: number, moldPct: number, sproutPct: number): LiveVerdict {
  if (darkPct >= 0.09 || moldPct >= 0.07) return 'STRONG DARK/SPORE COLORS';
  if (darkPct >= 0.025 || moldPct >= 0.02 || sproutPct >= 0.02) return 'SUSPECT DARK AREAS';
  return 'FRESH-LOOKING COLORS';
}

/** Sample one frame and run the on-device colour heuristic. Source is a
 *  video element, canvas or image; the sample is drawn at <=320px, in-memory. */
export function colorScanFrame(
  source: HTMLVideoElement | HTMLCanvasElement | HTMLImageElement,
): ColorScanResult {
  const t0 = performance.now();
  const srcW = (source as HTMLVideoElement).videoWidth || (source as HTMLImageElement).naturalWidth || source.width;
  const srcH = (source as HTMLVideoElement).videoHeight || (source as HTMLImageElement).naturalHeight || source.height;
  const scale = Math.min(1, MAX_SIDE / Math.max(srcW || 1, srcH || 1));
  const cw = Math.max(48, Math.round((srcW || 1) * scale));
  const ch = Math.max(48, Math.round((srcH || 1) * scale));

  const canvas = document.createElement('canvas');
  canvas.width = cw;
  canvas.height = ch;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) return { blobs: [], sampledAt: t0, frameWidth: cw, frameHeight: ch, frameMs: 0 };
  ctx.drawImage(source, 0, 0, cw, ch);
  const data = ctx.getImageData(0, 0, cw, ch).data;

  const gw = Math.max(2, Math.floor(cw / GRID));
  const gh = Math.max(2, Math.floor(ch / GRID));
  const label = new Int32Array(gw * gh).fill(0);
  const px = data;

  const gridClass = (gx: number, gy: number): number => {
    // average the GRIDxGRID cell (step sampling for speed)
    let sum = 0;
    let cnt = 0;
    const x0 = gx * GRID;
    const y0 = gy * GRID;
    for (let dy = 0; dy < GRID && y0 + dy < ch; dy += 2) {
      for (let dx = 0; dx < GRID && x0 + dx < cw; dx += 2) {
        const i = ((y0 + dy) * cw + (x0 + dx)) * 4;
        const r = px[i] / 255;
        const g = px[i + 1] / 255;
        const b = px[i + 2] / 255;
        const mx = Math.max(r, g, b);
        const mn = Math.min(r, g, b);
        const v = mx;
        const s = mx === 0 ? 0 : (mx - mn) / mx;
        let h = 0;
        if (s > 0) {
          if (mx === r) h = 60 * (((g - b) / (mx - mn)) % 6);
          else if (mx === g) h = 60 * ((b - r) / (mx - mn) + 2);
          else h = 60 * ((r - g) / (mx - mn) + 4);
          if (h < 0) h += 360;
        }
        const c = classify(h, s, v);
        sum += c === 0 ? 0 : 1;
        cnt++;
      }
    }
    // the cell "seed" is skin-coloured if a majority sample is any onion class
    return cnt > 0 && sum / cnt > 0.5 ? 1 : 0;
  };

  // connected components on the 6px grid (seed = skin/dark/mold/sprout cells)
  const blobs: GridBlob[] = [];
  let next = 1;
  const stack: number[] = [];
  for (let gstart = 0; gstart < gw * gh; gstart++) {
    if (label[gstart] !== 0 || gridClass(gstart % gw, Math.floor(gstart / gw)) === 0) continue;
    const id = next++;
    const blob: GridBlob = {
      n: 0, dark: 0, mold: 0, sprout: 0,
      skinN: 0, skinWarmCream: 0, hueHist: new Int32Array(18),
      x0: gw, y0: gh, x1: 0, y1: 0,
    };
    stack.push(gstart);
    label[gstart] = id;
    while (stack.length) {
      const p = stack.pop() as number;
      const gx = p % gw;
      const gy = (p / gw) | 0;
      blob.n++;
      blob.x0 = Math.min(blob.x0, gx);
      blob.y0 = Math.min(blob.y0, gy);
      blob.x1 = Math.max(blob.x1, gx);
      blob.y1 = Math.max(blob.y1, gy);
      // class majority within cell
      let dark = 0, mold = 0, sprout = 0, skin = 0, warmCream = 0;
      const hueHist = new Int32Array(18);
      const x0 = gx * GRID;
      const y0 = gy * GRID;
      for (let dy = 0; dy < GRID && y0 + dy < ch; dy += 2) {
        for (let dx = 0; dx < GRID && x0 + dx < cw; dx += 2) {
          const i = ((y0 + dy) * cw + (x0 + dx)) * 4;
          const r = px[i] / 255;
          const g = px[i + 1] / 255;
          const b = px[i + 2] / 255;
          const mx = Math.max(r, g, b);
          const mn = Math.min(r, g, b);
          const v = mx;
          const s = mx === 0 ? 0 : (mx - mn) / mx;
          let h = 0;
          if (s > 0) {
            if (mx === r) h = 60 * (((g - b) / (mx - mn)) % 6);
            else if (mx === g) h = 60 * ((b - r) / (mx - mn) + 2);
            else h = 60 * ((r - g) / (mx - mn) + 4);
            if (h < 0) h += 360;
          }
          const c = classify(h, s, v);
          if (c & C_DARK) dark++;
          if (c & C_MOLD) mold++;
          if (c & C_SPROUT) sprout++;
          if (c & C_SKIN) {
            skin++;
            if (c & C_CREAM) warmCream++;
            const bin = Math.min(17, Math.max(0, Math.floor(h / 20)));
            hueHist[bin]++;
          }
        }
      }
      blob.dark += dark;
      blob.mold += mold;
      blob.sprout += sprout;
      blob.skinN += skin;
      blob.skinWarmCream += warmCream;
      for (let b2 = 0; b2 < 18; b2++) blob.hueHist[b2] += hueHist[b2];
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
        const nx = gx + dx;
        const ny = gy + dy;
        if (nx < 0 || ny < 0 || nx >= gw || ny >= gh) continue;
        const q = ny * gw + nx;
        if (label[q] === 0 && gridClass(nx, ny) === 1) {
          label[q] = id;
          stack.push(q);
        }
      }
    }
    // min blob size: an onion ~5% of the frame width is a circle of ~3 cells
    if (blob.n >= 5) blobs.push(blob);
  }

  blobs.sort((a, b) => b.n - a.n);
  const out: LiveBlob[] = blobs.slice(0, 10).map((b) => {
    const total = Math.max(1, b.n * 4); // cells x 4 sampled px per cell
    const darkPct = b.dark / total;
    const moldPct = b.mold / total;
    const sproutPct = b.sprout / total;
    const { variety, confidence } = varietyFromBlob(b);
    return {
      x: b.x0 / gw,
      y: b.y0 / gh,
      width: (b.x1 - b.x0 + 1) / gw,
      height: (b.y1 - b.y0 + 1) / gh,
      verdict: verdictOf(darkPct, moldPct, sproutPct),
      darkPct,
      moldPct,
      sproutPct,
      variety,
      varietyConfidence: confidence,
      pixelCount: b.n,
    };
  });

  return { blobs: out, sampledAt: t0, frameWidth: cw, frameHeight: ch, frameMs: performance.now() - t0 };
}
