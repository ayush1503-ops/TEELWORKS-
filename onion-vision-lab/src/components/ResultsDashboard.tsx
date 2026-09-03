import { motion } from 'framer-motion';
import type { AnalyzeResponse, Finding, OnionResult, OnionStatus } from '../types/vision';
import { FINDING_TEXT, STATUS_COLORS, STATUS_TEXT, VARIETY_LABEL } from '../types/vision';
import { buildPdf } from './PdfReport';

interface Props {
  response: AnalyzeResponse;
  imageSrc: string;
  onInspect: (index: number) => void;
  onRescan: () => void;
}

const ORDER: OnionStatus[] = ['GREEN', 'YELLOW', 'RED'];

export default function ResultsDashboard({ response, imageSrc, onInspect, onRescan }: Props) {
  const counts = { GREEN: 0, YELLOW: 0, RED: 0 } as Record<OnionStatus, number>;
  response.results.forEach((r) => (counts[r.status] += 1));
  const demo = response.engine.includes('DEMO');
  const m = response.meta;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-2xl font-extrabold tracking-tight text-fg">Inspection results</h3>
          <p className="mono mt-1 text-xs text-mutext">
            {response.results.length} onion{response.results.length === 1 ? '' : 's'} · engine:{' '}
            <span className={`font-bold ${demo ? 'text-amber' : 'text-green'}`}>{response.engine}</span>
            {m?.timingsMs?.total ? ` · ${(m.timingsMs.total / 1000).toFixed(1)}s` : ''}
            {typeof m?.verifierDropped === 'number' && m.verifierDropped > 0
              ? ` · verifier rejected ${m.verifierDropped} non-onion detection${m.verifierDropped === 1 ? '' : 's'}`
              : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-ghost-light h-11 px-5 text-sm" onClick={onRescan}>
            ← new scan
          </button>
          <button className="btn-primary-blue h-11 px-5 text-sm" onClick={() => buildPdf(response, imageSrc)}>
            ⬇ PDF report
          </button>
        </div>
      </div>

      {/* status summary cards */}
      <div className="grid grid-cols-3 gap-3">
        {ORDER.map((s) => {
          const c = STATUS_COLORS[s];
          return (
            <motion.div
              key={s}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`glass rounded-2xl border p-4 shadow-soft ${c.text}`}
            >
              <div className="flex items-center gap-3">
                <span className={`h-3.5 w-3.5 rounded-full ${c.bar}`} />
                <div>
                  <div className="text-3xl font-extrabold leading-none">{counts[s]}</div>
                  <div className="tech-label mt-1.5 !text-[0.55rem]">
                    {s === 'GREEN' ? 'no obvious visible damage' : s === 'YELLOW' ? 'needs review' : 'visible damage'}
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {response.results.length === 0 && (
        <div className="glass rounded-2xl p-8 text-center shadow-soft">
          <div className="text-3xl">🧅</div>
          <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-mutext">
            <span className="font-bold text-fg">No onions detected in this image.</span> If the photo contains
            onions, try closer framing or better light. Nothing is inferred from absence.
          </p>
        </div>
      )}

      {/* per-onion cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {response.results.map((r, i) => (
          <OnionCard key={r.id} result={r} index={i} onInspect={onInspect} delay={Math.min(i * 0.05, 0.4)} />
        ))}
      </div>

      {/* model-signal summary */}
      <div className="glass rounded-2xl p-5 shadow-soft">
        <p className="tech-label text-mutext">why was this flagged? · model signals</p>
        <ModelSignals response={response} />
      </div>

      {/* disclaimers */}
      <ul className="space-y-1.5 pb-4">
        {(response.meta.disclaimers ?? []).map((d, i) => (
          <li key={i} className="mono flex gap-2 text-[11px] leading-relaxed text-mutext">
            <span className="text-electric">•</span>
            <span>{d}</span>
          </li>
        ))}
        <li className="mono flex gap-2 text-[11px] leading-relaxed text-mutext">
          <span className="text-electric">•</span>
          <span>Variety labels are colour ESTIMATES from the visible skin — never ground truth.</span>
        </li>
      </ul>
    </div>
  );
}

function OnionCard({
  result: r,
  index,
  onInspect,
  delay,
}: {
  result: OnionResult;
  index: number;
  onInspect: (i: number) => void;
  delay: number;
}) {
  const c = STATUS_COLORS[r.status];
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className={`glass rounded-2xl border p-4 shadow-soft ${c.text}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="mono text-[11px] text-mutext">{r.id}</div>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2.5 py-1 text-xs font-bold ${c.chip}`}>{r.statusLabel}</span>
            <span
              className="mono rounded-full border border-line bg-white px-2 py-1 text-[10px] text-mutext"
              title="Colour estimate of the variety from visible skin - not ground truth"
            >
              {VARIETY_LABEL[r.variety]} · est.
            </span>
          </div>
          <p className="mt-2 max-w-md text-xs leading-relaxed text-mutext">{STATUS_TEXT[r.status]}</p>
        </div>
        <div className="text-right">
          <div className="text-xl font-extrabold text-fg">{(r.confidence * 100).toFixed(0)}%</div>
          <div className="tech-label text-mutext">visual conf.*</div>
        </div>
      </div>

      {r.findings.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {r.findings.map((f, k) => (
            <FindingRow key={k} f={f} />
          ))}
        </ul>
      ) : (
        <p className="mt-3 rounded-xl border border-green/20 bg-greenSoft/60 p-2.5 text-xs text-mutext">
          No visible damage cues measured on the photographed surface.
        </p>
      )}

      <div className="mono mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-mutext">
        <span>dark {r.metrics.darkRatio.toFixed(3)}</span>
        <span>satσ {r.metrics.saturationStd.toFixed(1)}</span>
        <span>greenTop {r.metrics.greenTop.toFixed(3)}</span>
        <span>det {r.metrics.detectorConfidence.toFixed(2)}</span>
        {r.metrics.verifierConfidence != null && <span>verify {r.metrics.verifierConfidence.toFixed(2)}</span>}
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="mono max-w-[55%] truncate text-[10px] text-mutext" title={r.modelName}>
          {r.modelName}
        </span>
        <button className="btn-ghost-light !rounded-lg px-3.5 py-1.5 text-xs" onClick={() => onInspect(index)}>
          3D inspect →
        </button>
      </div>
    </motion.div>
  );
}

function FindingRow({ f }: { f: Finding }) {
  return (
    <li className="rounded-xl border border-line bg-white p-2.5 text-xs shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-bold text-fg">{f.kind}</span>
        <span className="mono text-[10px] text-mutext">{(f.confidence * 100).toFixed(0)}% visual evidence</span>
      </div>
      <p className="mt-1 leading-relaxed text-mutext">
        {FINDING_TEXT[f.kind]} — {f.evidence}
      </p>
    </li>
  );
}

function ModelSignals({ response }: { response: AnalyzeResponse }) {
  const withSignals = response.results.filter((r) => r.signals && (r.signals.cnn || r.signals.rf));
  if (withSignals.length === 0) {
    return (
      <p className="mt-2 text-xs text-mutext">
        {response.engine.includes('DEMO')
          ? 'local heuristic engine — no model signals (DEMO mode)'
          : 'per-model signals unavailable for this run'}
      </p>
    );
  }
  const names = ['clear', 'review', 'suspect'] as const;
  return (
    <div className="mt-3 grid gap-3 lg:grid-cols-2">
      {withSignals.slice(0, 4).map((r) => (
        <div key={r.id} className="rounded-xl border border-line bg-white p-3 shadow-sm">
          <div className="mono mb-2 text-[10px] text-mutext">
            {r.id} · {r.statusLabel.toLowerCase()} · fusion: {r.notes ?? 'n/a'}
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(['cnn', 'rf', 'heuristic'] as const).map((k) => {
              const sig = r.signals?.[k];
              return (
                <div key={k}>
                  <div className="tech-label mb-1 text-mutext">
                    {k === 'cnn' ? 'pytorch cnn' : k === 'rf' ? 'sklearn rf' : 'hsv heuristic'}
                  </div>
                  {sig ? (
                    sig.map((p, j) => (
                      <div key={j} className="flex items-center gap-1.5">
                        <div className="h-1.5 flex-1 overflow-hidden rounded bg-slate-100">
                          <div
                            className={j === 2 ? 'h-full bg-red' : j === 1 ? 'h-full bg-amber' : 'h-full bg-green'}
                            style={{ width: `${Math.round(p * 100)}%` }}
                          />
                        </div>
                        <span className="mono w-9 text-right text-[9px] text-mutext">{(p * 100).toFixed(0)}%</span>
                      </div>
                    ))
                  ) : (
                    <div className="mono text-[9px] text-mutext/60">n/a</div>
                  )}
                </div>
              );
            })}
          </div>
          <div className="mono mt-2 text-[9px] text-mutext/70">bars: {names.join(' / ')} · fused by calibrated logistic meta-learner</div>
        </div>
      ))}
    </div>
  );
}
