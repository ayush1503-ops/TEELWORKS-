/**
 * THE single vision contract. Every engine (remote inference API, local HSV
 * heuristic demo) must produce OnionResult[]. The UI knows nothing else.
 */

export type OnionStatus = 'GREEN' | 'YELLOW' | 'RED';

export type StatusLabel =
  | 'NO OBVIOUS VISIBLE DAMAGE'
  | 'NEEDS REVIEW'
  | 'VISIBLE DAMAGE';

/** colour-family ESTIMATE of the variety from visible skin — never ground truth */
export type OnionVariety = 'RED' | 'GOLDEN' | 'PURPLE' | 'WHITE' | 'UNKNOWN';

export type FindingKind =
  | 'Surface Discoloration'
  | 'Surface Damage'
  | 'Possible Mold-Like Growth'
  | 'Shriveling'
  | 'Sprouting';

export interface BBox {
  /** normalized 0..1 */
  x: number;
  y: number;
  width: number;
  height: number;
}

/** normalized position + radius of a suspected region INSIDE the onion crop */
export interface RegionPoint {
  x: number;
  y: number;
  r: number;
}

export interface Finding {
  kind: FindingKind;
  /** visual-evidence strength 0..1 - NEVER a food-safety probability */
  confidence: number;
  evidence: string;
}

export interface OnionMetrics {
  darkRatio: number;
  saturationStd: number;
  greenTop: number;
  detectorConfidence: number;
  verifierConfidence?: number | null;
}

export interface ModelSignals {
  cnn?: [number, number, number] | null;
  rf?: [number, number, number] | null;
  heuristic?: [number, number, number] | null;
}

export interface OnionResult {
  id: string;
  bbox: BBox;
  status: OnionStatus;
  statusLabel: StatusLabel;
  /** the model's visual prediction confidence only */
  confidence: number;
  findings: Finding[];
  regions: RegionPoint[];
  metrics: OnionMetrics;
  modelName: string;
  notes?: string;
  signals?: ModelSignals;
  /** colour-family estimate (RED/GOLDEN/PURPLE/WHITE/UNKNOWN) — an estimate */
  variety: OnionVariety;
  varietyConfidence: number;
}

export type SourceMode = 'camera' | 'upload' | 'demo';

export interface AnalyzeMeta {
  sourceMode: SourceMode;
  detectedRaw?: number;
  verifierDropped?: number;
  kept?: number;
  timingsMs?: { detect?: number; 'condition+verify'?: number; total?: number };
  ensembleAvailable?: { cnn: boolean; rf: boolean; meta: boolean };
  fusion?: string;
  disclaimers?: string[];
}

export interface AnalyzeResponse {
  engine: string;
  engineDetail: string;
  imageWidth: number;
  imageHeight: number;
  results: OnionResult[];
  meta: AnalyzeMeta;
}

/* ------------------------------------------------------------------ *
 * plain-language helpers — numbers always travel WITH meaning (F8)
 * ------------------------------------------------------------------ */

export const STATUS_TEXT: Record<OnionStatus, string> = {
  GREEN: 'No obvious visible damage on the surface that was photographed.',
  YELLOW: 'Something on the skin deserves a closer look — e.g. dark patches seen on the skin.',
  RED: 'Clear visible signs of damage were found on the skin.',
};

export const STATUS_COLORS: Record<OnionStatus, { text: string; chip: string; bar: string; hex: string }> = {
  GREEN: { text: 'text-green', chip: 'bg-greenSoft text-green border-green/25', bar: 'bg-green', hex: '#16A34A' },
  YELLOW: { text: 'text-amber', chip: 'bg-amberSoft text-amber border-amber/25', bar: 'bg-amber', hex: '#D97706' },
  RED: { text: 'text-red', chip: 'bg-redSoft text-red border-red/25', bar: 'bg-red', hex: '#DC2626' },
};

export const VARIETY_LABEL: Record<OnionVariety, string> = {
  RED: 'Red variety',
  GOLDEN: 'Golden / yellow',
  PURPLE: 'Purple / violet',
  WHITE: 'White / cream',
  UNKNOWN: 'Colour not clear',
};

/** human sentence for each finding (kept in the findings vocabulary only) */
export const FINDING_TEXT: Record<FindingKind, string> = {
  'Surface Discoloration': 'darker or uneven colour patches on the skin',
  'Surface Damage': 'cuts, marks or broken-looking skin',
  'Possible Mold-Like Growth': 'grey/green fuzzy-looking spots that could be mould',
  Shriveling: 'dry, wrinkled-looking skin',
  Sprouting: 'a green shoot is starting to grow',
};

export const INTERNAL_QUALITY_NOTE =
  'Internal quality cannot be determined by any camera — black mold inside or hollow heart stay invisible. Manual cutting remains the only check.';
