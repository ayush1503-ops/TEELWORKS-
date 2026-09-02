/**
 * THE single vision contract. Every engine (remote inference API, local HSV
 * heuristic demo) must produce OnionResult[]. The UI knows nothing else.
 */

export type OnionStatus = 'GREEN' | 'YELLOW' | 'RED';

export type StatusLabel =
  | 'NO OBVIOUS VISIBLE DAMAGE'
  | 'NEEDS REVIEW'
  | 'VISIBLE DAMAGE';

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

export const STATUS_COLORS: Record<OnionStatus, string> = {
  GREEN: 'text-lab-green border-lab-green/40 bg-lab-green/10',
  YELLOW: 'text-lab-amber border-lab-amber/40 bg-lab-amber/10',
  RED: 'text-lab-red border-lab-red/40 bg-lab-red/10',
};

export const STATUS_DOT: Record<OnionStatus, string> = {
  GREEN: 'bg-lab-green',
  YELLOW: 'bg-lab-amber',
  RED: 'bg-lab-red',
};
