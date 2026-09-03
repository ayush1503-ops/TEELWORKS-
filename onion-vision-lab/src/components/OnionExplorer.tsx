import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import type { AnalyzeResponse, OnionResult } from '../types/vision';
import { FINDING_TEXT, INTERNAL_QUALITY_NOTE, STATUS_COLORS, STATUS_TEXT, VARIETY_LABEL } from '../types/vision';
import OnionModel from './OnionModel';

interface Props {
  response: AnalyzeResponse | null;
  imageSrc: string | null;
  selected: number | null;
  onSelect: (i: number | null) => void;
  onBackToResults: () => void;
}

/** crop a detection square out of the source image (in-memory, pad 8%) */
function cropToDataUrl(srcUrl: string, bbox: { x: number; y: number; width: number; height: number }): Promise<string> {
  return new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => {
      const w = im.naturalWidth;
      const h = im.naturalHeight;
      const pad = 0.08;
      let x0 = Math.max(0, (bbox.x - pad) * w);
      let y0 = Math.max(0, (bbox.y - pad) * h);
      let x1 = Math.min(w, (bbox.x + bbox.width + pad) * w);
      let y1 = Math.min(h, (bbox.y + bbox.height + pad) * h);
      // force square around the onion centre
      const cw0 = x1 - x0;
      const ch0 = y1 - y0;
      const side = Math.max(cw0, ch0);
      const cx = (x0 + x1) / 2;
      const cy = (y0 + y1) / 2;
      x0 = Math.max(0, cx - side / 2);
      y0 = Math.max(0, cy - side / 2);
      x0 = Math.min(x0, w - side);
      y0 = Math.min(y0, h - side);
      const c = document.createElement('canvas');
      c.width = side;
      c.height = side;
      const g = c.getContext('2d');
      if (!g) {
        reject(new Error('no canvas'));
        return;
      }
      g.drawImage(im, x0, y0, side, side, 0, 0, side, side);
      resolve(c.toDataURL('image/jpeg', 0.9));
    };
    im.onerror = () => reject(new Error('image decode failed'));
    im.src = srcUrl;
  });
}

export default function OnionExplorer({ response, imageSrc, selected, onSelect, onBackToResults }: Props) {
  const result: OnionResult | null =
    response && imageSrc && selected != null && response.results[selected] ? response.results[selected] : null;
  const [cropUrl, setCropUrl] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setCropUrl(null);
    if (result && imageSrc) {
      cropToDataUrl(imageSrc, result.bbox)
        .then((url) => alive && setCropUrl(url))
        .catch(() => alive && setCropUrl(null));
    }
    return () => {
      alive = false;
    };
  }, [result, imageSrc]);

  return (
    <section id="explorer" className="relative scroll-mt-20 overflow-hidden py-20 md:py-24">
      <div className="pointer-events-none absolute right-0 top-16 h-[420px] w-[420px] rounded-full bg-electric/8 blur-[130px]" />
      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <p className="tech-label text-electric">3D Explorer / deep analysis</p>
        <h2 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-fg md:text-5xl">
          Inspect one onion, <span className="text-gradient-blue">honestly</span>
        </h2>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-mutext">
          Every captured onion can be opened in the 3D explorer: the photographed
          crop is wrapped onto a procedural onion and its findings are traced back
          through the model signals. Only the photographed side is real evidence.
        </p>

        {!result ? (
          <EmptyExplorer onSelect={onSelect} response={response} onBackToResults={onBackToResults} />
        ) : (
          <motion.div key={result.id} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="mt-10 grid gap-6 lg:grid-cols-2">
            {/* 3D viewer */}
            <div className="glass relative overflow-hidden rounded-3xl shadow-lift">
              <div className="scanlines pointer-events-none absolute inset-0 z-10" />
              <div className="absolute left-4 top-4 z-20">
                <p className="tech-label rounded-full bg-white/90 px-2.5 py-1 text-electric shadow-sm">3D · photo-textured</p>
              </div>
              <OnionModel height={480} textureUrl={cropUrl} damage={result.regions} />
              <div className="absolute inset-x-4 bottom-4 z-20 space-y-1.5">
                {result.regions.length > 0 ? (
                  <div className="mono rounded-xl bg-white/95 px-3 py-2 text-[10px] font-semibold leading-relaxed text-red shadow-sm">
                    ● AI-INFERRED REGION{result.regions.length > 1 ? ` (+${result.regions.length - 1} more)` : ''} —
                    suspected damage location inferred from image cues, not a measured internal defect
                  </div>
                ) : (
                  <div className="mono rounded-xl bg-white/95 px-3 py-2 text-[10px] font-semibold text-green shadow-sm">
                    no suspected regions flagged on the visible surface
                  </div>
                )}
                <div className="mono rounded-xl bg-white/95 px-3 py-2 text-[10px] leading-relaxed text-mutext shadow-sm">
                  caption honesty: only the photographed side is real evidence — the far side repeats the photographed
                  texture (it was not photographed)
                </div>
              </div>
            </div>

            {/* findings, layers, signals */}
            <div className="space-y-4">
              <VerdictPanel result={result} onBackToResults={onBackToResults} onSelect={onSelect} />
              <LayersPanel result={result} />
              <SignalTrace result={result} />
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
}

function EmptyExplorer({
  onSelect,
  response,
  onBackToResults,
}: {
  onSelect: (i: number | null) => void;
  response: AnalyzeResponse | null;
  onBackToResults: () => void;
}) {
  const hasAny = (response?.results.length ?? 0) > 0;
  return (
    <div className="mt-10 grid gap-6 lg:grid-cols-2">
      <div className="glass relative overflow-hidden rounded-3xl shadow-lift">
        <OnionModel height={420} />
        <div className="pointer-events-none absolute bottom-4 left-4 right-4">
          <div className="mono rounded-xl bg-white/95 px-3 py-2 text-[10px] leading-relaxed text-mutext shadow-sm">
            reference model — procedural skin, no photo yet
          </div>
        </div>
      </div>
      <div className="glass flex flex-col justify-center rounded-3xl p-8 shadow-soft">
        {hasAny ? (
          <>
            <p className="tech-label text-electric">pick an onion</p>
            <h3 className="mt-2 text-xl font-extrabold text-fg">Choose one of the scanned onions</h3>
            <p className="mt-2 text-sm leading-relaxed text-mutext">
              Use the “3D inspect →” button on any onion card in the results, or tap a tracking circle on the photo.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {response?.results.slice(0, 10).map((r, i) => (
                <button key={r.id} onClick={() => onSelect(i)} className="btn-ghost-light rounded-full px-4 py-1.5 text-xs">
                  {r.id} · {r.statusLabel}
                </button>
              ))}
            </div>
            <button onClick={onBackToResults} className="btn-ghost-light mt-6 self-start px-5 py-2.5 text-sm">
              ← back to results
            </button>
          </>
        ) : (
          <>
            <p className="tech-label text-electric">scan first</p>
            <h3 className="mt-2 text-xl font-extrabold text-fg">Nothing to explore yet</h3>
            <p className="mt-2 text-sm leading-relaxed text-mutext">
              Run a scan in the Vision Lab above — then open any onion here for its photo-textured 3D view,
              layer-by-layer analysis and full model-signal trace.
            </p>
            <a href="#vision-lab" className="btn-primary-blue mt-6 self-start px-6 py-2.5 text-sm">
              go to the scanner
            </a>
          </>
        )}
      </div>
    </div>
  );
}

function VerdictPanel({
  result,
  onBackToResults,
  onSelect,
}: {
  result: OnionResult;
  onBackToResults: () => void;
  onSelect: (i: number | null) => void;
}) {
  const c = STATUS_COLORS[result.status];
  return (
    <div className={`glass rounded-2xl border p-5 shadow-soft ${c.text}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="mono text-[11px] text-mutext">{result.id} · deep analysis</div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-sm font-extrabold ${c.chip}`}>{result.statusLabel}</span>
            <span
              className="mono rounded-full border border-line bg-white px-2.5 py-1 text-[10px] text-mutext"
              title="colour estimate of the variety from visible skin — not ground truth"
            >
              {VARIETY_LABEL[result.variety]} · est. · {(result.varietyConfidence * 100).toFixed(0)}% agree
            </span>
          </div>
          <p className="mt-2 max-w-md text-xs leading-relaxed text-mutext">{STATUS_TEXT[result.status]}</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-extrabold text-fg">{(result.confidence * 100).toFixed(0)}%</div>
          <div className="tech-label text-mutext">visual conf.*</div>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={onBackToResults} className="btn-ghost-light px-4 py-2 text-xs">
          ← back to results
        </button>
        <button onClick={() => onSelect(null)} className="btn-ghost-light px-4 py-2 text-xs">
          close deep analysis
        </button>
      </div>
    </div>
  );
}

function LayersPanel({ result }: { result: OnionResult }) {
  const findingsLabel =
    result.findings.length > 0
      ? result.findings.map((f) => `${f.kind} (${(f.confidence * 100).toFixed(0)}%)`).join(' · ')
      : 'no damage cues measured on the visible surface';
  const layers: Array<{ id: string; name: string; tag: string; tagColor: string; text: string }> = [
    {
      id: 'L1',
      name: 'Outer papery skin',
      tag: 'MEASURED',
      tagColor: 'bg-greenSoft text-green border-green/25',
      text: findingsLabel,
    },
    {
      id: 'L2',
      name: 'Outer fleshy scales',
      tag: 'NOT VISIBLE',
      tagColor: 'bg-amberSoft text-amber border-amber/25',
      text: 'Under the papery skin — not visible to the camera, so nothing is claimed about them.',
    },
    {
      id: 'L3',
      name: 'Inner scales & flesh',
      tag: 'NOT VISIBLE',
      tagColor: 'bg-amberSoft text-amber border-amber/25',
      text: INTERNAL_QUALITY_NOTE,
    },
    {
      id: 'L4',
      name: 'Basal plate & roots',
      tag: 'NOT CAPTURED',
      tagColor: 'bg-redSoft text-red border-red/25',
      text: 'This onion was photographed from one side; the base was not captured in the photo.',
    },
  ];
  return (
    <div className="glass rounded-2xl p-5 shadow-soft">
      <p className="tech-label text-mutext">layer-by-layer analysis (F6)</p>
      <div className="mt-3 space-y-2">
        {layers.map((l) => (
          <div key={l.id} className="rounded-xl border border-line bg-white p-3 shadow-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-sm font-extrabold text-fg">
                {l.id} · {l.name}
              </span>
              <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold ${l.tagColor}`}>{l.tag}</span>
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-mutext">{l.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SignalTrace({ result }: { result: OnionResult }) {
  const names = ['clear', 'review', 'suspect'] as const;
  const bars: Array<{ key: 'cnn' | 'rf' | 'heuristic'; label: string; probs: [number, number, number] | null | undefined }> = [
    { key: 'cnn', label: 'PyTorch CNN (MobileNetV2)', probs: result.signals?.cnn },
    { key: 'rf', label: 'sklearn RandomForest (calibrated)', probs: result.signals?.rf },
    { key: 'heuristic', label: 'HSV heuristic (OpenCV cues)', probs: result.signals?.heuristic },
  ];
  return (
    <div className="glass rounded-2xl p-5 shadow-soft">
      <p className="tech-label text-mutext">model-signal trace (what the verdict is made of)</p>
      <div className="mt-3 space-y-3">
        <StepRow
          label="1 · Detector (YOLOv8n, ONNX)"
          value={`conf ${result.metrics.detectorConfidence.toFixed(3)} — found the onion in the photo`}
        />
        <StepRow
          label="2 · Verifier gate (TensorFlow)"
          value={
            result.metrics.verifierConfidence != null
              ? `p(onion) ${result.metrics.verifierConfidence.toFixed(3)} — passed the onion-vs-not-onion check`
              : 'verifier not available in this run'
          }
        />
        <div className="rounded-xl border border-line bg-white p-3 shadow-sm">
          <div className="text-xs font-bold text-fg">3 · Condition signals → probs [clear · review · suspect]</div>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {bars.map((b) => (
              <div key={b.key}>
                <div className="tech-label mb-1 text-mutext">{b.label}</div>
                {b.probs ? (
                  b.probs.map((p, j) => (
                    <div key={j} className="flex items-center gap-1.5">
                      <div className="h-1.5 flex-1 overflow-hidden rounded bg-slate-100">
                        <div
                          className={j === 2 ? 'h-full bg-red' : j === 1 ? 'h-full bg-amber' : 'h-full bg-green'}
                          style={{ width: `${Math.round(p * 100)}%` }}
                        />
                      </div>
                      <span className="mono w-8 text-right text-[9px] text-mutext">{(p * 100).toFixed(0)}%</span>
                    </div>
                  ))
                ) : (
                  <div className="mono text-[9px] text-mutext/60">n/a</div>
                )}
              </div>
            ))}
          </div>
          <div className="mono mt-2 text-[9px] text-mutext/70">
            bars: {names.join(' / ')} · {result.notes ?? 'fused by calibrated logistic meta-learner'}
          </div>
        </div>
        <div className="rounded-xl border border-electric/25 bg-electricSoft p-3">
          <div className="text-xs font-extrabold text-electric">4 · Fused verdict</div>
          <p className="mt-1 text-xs leading-relaxed text-mutext">
            {result.statusLabel} ({(result.confidence * 100).toFixed(0)}% visual confidence). The meta-learner mixes
            the three signals above; the confidence is about what the models see on the skin — never a food-safety
            probability.
          </p>
        </div>
      </div>
      <p className="mt-3 text-[11px] italic leading-relaxed text-mutext">
        Findings vocabulary is limited to: {Object.keys(FINDING_TEXT).join(' · ')}.
      </p>
    </div>
  );
}

function StepRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-white p-3 shadow-sm">
      <div className="text-xs font-bold text-fg">{label}</div>
      <p className="mono mt-1 text-[11px] text-mutext">{value}</p>
    </div>
  );
}

export { cropToDataUrl };
export type OnionExplorerProps = Props;
