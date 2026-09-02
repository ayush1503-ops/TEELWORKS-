import { motion } from 'framer-motion';
import type { AnalyzeResponse, OnionResult } from '../types/vision';
import { STATUS_COLORS, STATUS_DOT } from '../types/vision';
import { buildPdf } from './PdfReport';

interface Props {
  response: AnalyzeResponse;
  imageSrc: string;
  onInspect: (index: number) => void;
  onRescan: () => void;
}

export function ResultsDashboard({ response, imageSrc, onInspect, onRescan }: Props) {
  const counts = { GREEN: 0, YELLOW: 0, RED: 0 } as Record<OnionResult['status'], number>;
  response.results.forEach((r) => (counts[r.status] += 1));
  const demo = response.engine.includes('DEMO');
  const m = response.meta;

  return (
    <div className="mx-auto w-full max-w-5xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Inspection results</h2>
          <p className="mono text-xs text-violet-200/60">
            {response.results.length} onion{response.results.length === 1 ? '' : 's'} · engine:{' '}
            <span className={demo ? 'text-lab-amber' : 'text-lab-green'}>{response.engine}</span>
            {m?.timingsMs?.total ? ` · ${(m.timingsMs.total / 1000).toFixed(2)}s` : ''}
            {typeof m?.verifierDropped === 'number' && m.verifierDropped > 0
              ? ` · verifier rejected ${m.verifierDropped} non-onion detection${m.verifierDropped === 1 ? '' : 's'}`
              : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={onRescan}>
            ← new scan
          </button>
          <button className="btn-primary" onClick={() => buildPdf(response, imageSrc)}>
            ⬇ PDF report
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {(['GREEN', 'YELLOW', 'RED'] as const).map((s) => (
          <motion.div
            key={s}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`panel flex items-center gap-3 p-4 ${STATUS_COLORS[s]}`}
          >
            <span className={`h-3 w-3 rounded-full ${STATUS_DOT[s]}`} />
            <div>
              <div className="text-2xl font-bold">{counts[s]}</div>
              <div className="text-[11px] uppercase tracking-wide opacity-80">
                {s === 'GREEN' ? 'no obvious visible damage' : s === 'YELLOW' ? 'needs review' : 'visible damage'}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {response.results.length === 0 && (
        <div className="panel p-6 text-center text-sm text-violet-200/70">
          No onions detected in this image. If the photo contains onions, try
          closer framing or better light. Nothing is inferred from absence.
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {response.results.map((r, i) => (
          <motion.div
            key={r.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.05, 0.5) }}
            className={`panel p-4 ${STATUS_COLORS[r.status]}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="mono text-xs opacity-70">{r.id}</div>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${STATUS_DOT[r.status]}`} />
                  <span className="text-sm font-bold tracking-wide">{r.statusLabel}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xl font-bold">{(r.confidence * 100).toFixed(0)}%</div>
                <div className="mono text-[9px] uppercase opacity-60">visual conf.*</div>
              </div>
            </div>

            {r.findings.length > 0 ? (
              <ul className="mt-3 space-y-2">
                {r.findings.map((f, k) => (
                  <li key={k} className="rounded-lg bg-black/25 p-2.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold">{f.kind}</span>
                      <span className="mono opacity-70">{(f.confidence * 100).toFixed(0)}% evidence</span>
                    </div>
                    <p className="mt-1 leading-relaxed text-violet-200/70">{f.evidence}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 rounded-lg bg-black/25 p-2.5 text-xs text-violet-200/60">
                No visible damage cues measured on the visible surface.
              </p>
            )}

            <div className="mono mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-violet-200/50">
              <span>dark {r.metrics.darkRatio.toFixed(3)}</span>
              <span>satσ {r.metrics.saturationStd.toFixed(1)}</span>
              <span>greenTop {r.metrics.greenTop.toFixed(3)}</span>
              <span>det {r.metrics.detectorConfidence.toFixed(2)}</span>
              {r.metrics.verifierConfidence != null && <span>verify {r.metrics.verifierConfidence.toFixed(2)}</span>}
            </div>

            <div className="mt-3 flex items-center justify-between">
              <span className="mono text-[10px] text-violet-200/40">{r.modelName}</span>
              <button className="btn-ghost !px-3 !py-1 text-xs" onClick={() => onInspect(i)}>
                3D inspect →
              </button>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="panel p-4">
        <div className="mono text-[10px] uppercase tracking-widest text-violet-200/40">
          why was this flagged? · model signals
        </div>
        <ModelSignals response={response} />
      </div>

      <ul className="space-y-1 pb-6">
        {(response.meta.disclaimers ?? DEFAULT_DISCLAIMERS).map((d, i) => (
          <li key={i} className="mono text-[10px] leading-relaxed text-violet-200/40">
            ⚠ {d}
          </li>
        ))}
      </ul>
    </div>
  );
}

const DEFAULT_DISCLAIMERS = [
  'Analysis is limited to the VISIBLE surface captured in the image.',
  'Internal quality cannot be determined by any camera.',
  'Confidence = the model visual prediction confidence only, not a food-safety probability.',
];

function ModelSignals({ response }: { response: AnalyzeResponse }) {
  const withSignals = response.results.filter((r) => r.signals && (r.signals.cnn || r.signals.rf));
  if (withSignals.length === 0) {
    return (
      <p className="mono mt-2 text-xs text-violet-200/50">
        {response.engine.includes('DEMO')
          ? 'local heuristic engine - no model signals (DEMO mode)'
          : 'per-model signals unavailable for this run'}
      </p>
    );
  }
  const names = ['clear', 'review', 'suspect'] as const;
  return (
    <div className="mt-3 space-y-3">
      {withSignals.slice(0, 4).map((r) => (
        <div key={r.id} className="rounded-lg bg-black/25 p-2.5">
          <div className="mono mb-2 text-[10px] text-violet-200/60">
            {r.id} · {r.statusLabel.toLowerCase()} · fusion: {r.notes}
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(['cnn', 'rf', 'heuristic'] as const).map((k) => {
              const sig = r.signals?.[k];
              return (
                <div key={k}>
                  <div className="mono mb-1 text-[9px] uppercase text-violet-200/40">
                    {k === 'cnn' ? 'pytorch cnn' : k === 'rf' ? 'sklearn rf' : 'hsv heuristic'}
                  </div>
                  {sig ? (
                    sig.map((p, j) => (
                      <div key={j} className="flex items-center gap-1.5">
                        <div className="h-1.5 flex-1 overflow-hidden rounded bg-white/5">
                          <div
                            className={j === 2 ? 'h-full bg-lab-red' : j === 1 ? 'h-full bg-lab-amber' : 'h-full bg-lab-green'}
                            style={{ width: `${Math.round(p * 100)}%` }}
                          />
                        </div>
                        <span className="mono w-9 text-right text-[9px] text-violet-200/50">
                          {(p * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="mono text-[9px] text-violet-200/30">n/a</div>
                  )}
                </div>
              );
            })}
          </div>
          <div className="mono mt-2 text-[9px] text-violet-200/40">
            bars: {names.join(' / ')} · fused by calibrated logistic meta-learner
          </div>
        </div>
      ))}
    </div>
  );
}
