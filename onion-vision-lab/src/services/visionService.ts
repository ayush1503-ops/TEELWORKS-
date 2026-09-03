/**
 * Engine selector - the ONLY place that knows engines exist.
 *
 * Priority: VITE_VISION_API env var controls the API base URL:
 *   - Not set / undefined  → '/vision-api'  (Vite dev-server proxies to localhost:8788)
 *   - Set to empty string  → ''             (same-origin deployment)
 *   - Set to a URL         → that URL       (cross-origin explicit override)
 *
 * If the remote API cannot be reached or fails, we degrade gracefully to
 * the in-browser HSV heuristic and label the engine DEMO. The UI consumes
 * OnionResult[] either way — and every DEMO badge is truthful.
 */

import type { AnalyzeResponse, SourceMode } from '../types/vision';
import { localHeuristicAnalyze } from './localHeuristic';

const _envBase = import.meta.env.VITE_VISION_API as string | undefined;
export const REMOTE_BASE: string = _envBase !== undefined ? _envBase : '/vision-api';

export interface EngineInfo {
  kind: 'remote' | 'local';
  label: string;
  detail: string;
  live: boolean;
}

export function getEngine(): EngineInfo {
  return {
    kind: 'remote',
    label: 'REMOTE INFERENCE API',
    detail: `${REMOTE_BASE}/api/analyze (YOLOv8n + TF verifier + fused condition ensemble)`,
    live: true,
  };
}

async function remoteAnalyze(imageBase64: string, sourceMode: SourceMode): Promise<AnalyzeResponse> {
  const res = await fetch(`${REMOTE_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ imageBase64, sourceMode }),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`vision API ${res.status}: ${detail.slice(0, 140)}`);
  }
  return (await res.json()) as AnalyzeResponse;
}

export async function analyzeImage(
  image: HTMLImageElement | HTMLCanvasElement,
  sourceMode: SourceMode,
): Promise<AnalyzeResponse> {
  const dataUrl = toJpegDataUrl(image, 2000);
  const payload = dataUrl.split(',')[1] ?? '';
  try {
    const out = await remoteAnalyze(payload, sourceMode);
    return { ...out, engine: out.engine || 'REMOTE INFERENCE API' };
  } catch (err) {
    // graceful degradation - honest DEMO label, never a silent fake
    console.warn('[vision] remote engine unavailable, falling back to local DEMO heuristic:', err);
    const local = localHeuristicAnalyze(image, sourceMode);
    local.meta.disclaimers = [
      `REMOTE ENGINE UNAVAILABLE (${String(err).slice(0, 120)}). Showing LOCAL DEMO heuristic results.`,
      ...(local.meta.disclaimers ?? []),
    ];
    return local;
  }
}

function toJpegDataUrl(src: HTMLImageElement | HTMLCanvasElement, maxSide: number): string {
  const w = (src as HTMLImageElement).naturalWidth || src.width;
  const h = (src as HTMLImageElement).naturalHeight || src.height;
  const scale = Math.min(1, maxSide / Math.max(w, h));
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(w * scale));
  c.height = Math.max(1, Math.round(h * scale));
  const ctx = c.getContext('2d');
  if (!ctx) throw new Error('canvas unavailable');
  ctx.drawImage(src, 0, 0, c.width, c.height);
  return c.toDataURL('image/jpeg', 0.9);
}

/* ---------------------------- health ---------------------------- */

export interface HealthJson {
  status?: string;
  service?: string;
  version?: string;
  engine?: string;
  pipeline?: {
    detector?: {
      loaded?: boolean;
      architecture?: string;
      conf?: number;
      inputSize?: number;
      measured?: Record<string, unknown>;
    };
    verifier?: {
      loaded?: boolean;
      architecture?: string;
      gateThreshold?: number;
      measured?: Record<string, unknown>;
      gateMeasured?: Record<string, unknown>;
    };
    condition?: {
      architecture?: string;
      version?: string;
      available?: { cnn?: boolean; rf?: boolean; meta?: boolean };
      measured?: Record<string, unknown>;
    };
  };
  colourShift?: {
    variants?: Record<string, { precision?: number; recall?: number; f1?: number; note?: string }>;
    scope?: string;
  };
  metricsSource?: string;
  disclaimers?: string[];
}

export interface ProbeResult {
  ok: boolean;
  text: string;
  health: HealthJson | null;
}

export async function fetchHealthFull(): Promise<ProbeResult> {
  try {
    const res = await fetch(`${REMOTE_BASE}/api/health`);
    if (!res.ok) return { ok: false, text: `health ${res.status}`, health: null };
    const j = (await res.json()) as HealthJson;
    const parts: string[] = [];
    if (j.pipeline?.detector?.loaded) parts.push('YOLOv8n');
    if (j.pipeline?.verifier?.loaded) parts.push('TF-verifier');
    if (j.pipeline?.condition?.available?.cnn) parts.push('CNN');
    if (j.pipeline?.condition?.available?.rf) parts.push('RF');
    if (j.pipeline?.condition?.available?.meta) parts.push('meta-fusion');
    return { ok: true, text: parts.length ? parts.join(' + ') : String(j.status ?? 'ok'), health: j };
  } catch {
    return { ok: false, text: 'unreachable', health: null };
  }
}

/** short probe used by the navbar pill */
export async function probeHealth(): Promise<{ ok: boolean; text: string }> {
  const p = await fetchHealthFull();
  return { ok: p.ok, text: p.text };
}
