import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { fetchHealthFull, type HealthJson } from '../services/visionService';

function num(v: unknown, d = 3): string {
  if (typeof v !== 'number') return 'n/a';
  return v.toFixed(d);
}

function scopeOf(v: unknown): string {
  return typeof v === 'string' ? v : '';
}

export default function ProjectDashboard() {
  const [health, setHealth] = useState<HealthJson | null>(null);
  const [ok, setOk] = useState(false);
  const [errText, setErrText] = useState('connecting…');

  useEffect(() => {
    let alive = true;
    fetchHealthFull().then((p) => {
      if (!alive) return;
      setOk(p.ok);
      setErrText(p.ok ? '' : p.text);
      if (p.health) setHealth(p.health);
    });
    return () => {
      alive = false;
    };
  }, []);

  const det = health?.pipeline?.detector;
  const ver = health?.pipeline?.verifier;
  const cond = health?.pipeline?.condition;
  const condMeasured = (cond?.measured ?? {}) as Record<string, unknown>;
  const cnnTest = (condMeasured.cnn_test ?? {}) as Record<string, unknown>;
  const sel = (condMeasured.fusion_selection ?? {}) as Record<string, unknown>;
  const valF1 = (sel.val_macro_f1 ?? {}) as Record<string, unknown>;
  const fusionTest = (condMeasured.fusionTest ?? {}) as Record<string, unknown>;
  const cs = health?.colourShift;

  return (
    <section id="metrics" className="relative scroll-mt-20 overflow-hidden bg-[#F7F9FF] py-20 md:py-24">
      <div className="dot-grid-soft pointer-events-none absolute inset-0" />
      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="tech-label text-electric">Metrics dashboard / live</p>
            <h2 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-fg md:text-5xl">
              Measured numbers, <span className="text-gradient-blue">scoped numbers</span>
            </h2>
          </div>
          <span
            className={`tech-label self-start rounded-full border px-3.5 py-1.5 md:self-auto ${
              ok ? 'border-green/30 bg-greenSoft text-green' : 'border-amber/40 bg-amberSoft text-amber'
            }`}
          >
            {ok ? '● live from GET /api/health' : `● API ${errText || 'unreachable'} → see METRICS.md`}
          </span>
        </div>

        {!ok && (
          <div className="glass mt-10 rounded-2xl p-6 shadow-soft">
            <p className="text-sm text-mutext">
              The inference API is not reachable from this page right now, so live numbers cannot be shown here.
              Measured values with full scopes are always in{' '}
              <code className="mono rounded bg-slate-100 px-1.5 py-0.5 text-[12px]">vision-api/METRICS.md</code>.
            </p>
          </div>
        )}

        {ok && health && (
          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {/* detector */}
            <MetricCard
              title="1 · Detector — YOLOv8n (ONNX)"
              subtitle="finds every visible onion · letterbox 320 · conf 0.45"
              rows={[
                ['Precision', num(det?.measured?.precision)],
                ['Recall', num(det?.measured?.recall)],
                ['F1', num(det?.measured?.f1)],
                ['mAP50', num(det?.measured?.map50)],
                ['Negatives w/ detections', String(det?.measured?.negative_images_with_detections ?? 'n/a') + ' / 40'],
                ['Avg inference', `${num(det?.measured?.avg_inference_ms, 1)} ms/img`],
              ]}
              scope={scopeOf(det?.measured?.scope)}
            />
            {/* verifier */}
            <MetricCard
              title="2 · Verifier gate — TensorFlow (ONNX)"
              subtitle="onion-vs-not-onion check on every detection"
              rows={[
                ['Test accuracy', num((ver?.measured as Record<string, unknown>)?.test_binary_acc)],
                ['Test AUC', num((ver?.measured as Record<string, unknown>)?.test_auc)],
                ['Gate threshold τ', num(ver?.gateThreshold ?? 0.5)],
                ['Test confusion', String((ver?.measured as Record<string, unknown>)?.test_confusion_at_tau ?? 'n/a')],
              ]}
              scope={scopeOf((ver?.measured as Record<string, unknown>)?.scope)}
            />
            {/* condition */}
            <MetricCard
              title="3 · Condition — PyTorch CNN + RF + HSV fused"
              subtitle="per-onion visible verdict (clear · review · suspect)"
              rows={[
                ['CNN test accuracy', num(cnnTest.acc)],
                ['CNN test macro-F1', num(cnnTest.macro_f1)],
                ['Fused test accuracy', num((fusionTest.fused as Record<string, unknown>)?.accuracy)],
                ['Fused test macro-F1', num((fusionTest.fused as Record<string, unknown>)?.macro_f1)],
                ['VAL macro-F1 (selection)', num(valF1.fused, 4)],
              ]}
              scope={
                (condMeasured.data_scope as string) ??
                'frozen 12 test crops, programmatic synthetic damage over real crops from ONE field photo; field validation pending'
              }
            />
          </div>
        )}

        {/* colour shift table */}
        {ok && cs?.variants && (
          <div className="glass mt-5 overflow-x-auto rounded-2xl p-5 shadow-soft">
            <p className="tech-label text-mutext">colour-shift stress test — single-variety honesty</p>
            <table className="mt-3 w-full min-w-[560px] text-left text-xs">
              <thead>
                <tr className="border-b border-line text-mutext">
                  <th className="py-1.5 pr-3 font-bold">Variant</th>
                  <th className="py-1.5 pr-3 font-bold">Precision</th>
                  <th className="py-1.5 pr-3 font-bold">Recall</th>
                  <th className="py-1.5 pr-3 font-bold">F1</th>
                  <th className="py-1.5 pr-3 font-bold">Negatives fired</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(cs.variants).map(([k, v]) => (
                  <tr key={k} className="border-b border-line/60 text-fg">
                    <td className="py-2 pr-3 font-mono">{k}</td>
                    <td className="py-2 pr-3">{num(v.precision)}</td>
                    <td className="py-2 pr-3">{num(v.recall)}</td>
                    <td className="py-2 pr-3">
                      <span className={typeof v.f1 === 'number' && v.f1 < 0.6 ? 'font-bold text-red' : ''}>
                        {num(v.f1)}
                      </span>
                    </td>
                    <td className="py-2 pr-3">/ 40</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {cs.scope && <p className="mono mt-2 text-[10px] leading-relaxed text-mutext">scope: {cs.scope}</p>}
          </div>
        )}

        {/* honesty notes */}
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <div className="glass rounded-2xl p-5 shadow-soft">
            <p className="tech-label text-mutext">what these numbers do NOT mean</p>
            <ul className="mt-3 space-y-2 text-xs leading-relaxed text-mutext">
              <li>• Not field accuracy — every image derives from one field photo’s crops or from procedural generation.</li>
              <li>• Not food safety — confidence values are visual prediction confidences only.</li>
              <li>• Not internal quality — a camera cannot see inside an onion.</li>
              <li>• Not variety coverage — see the colour-shift table above.</li>
            </ul>
          </div>
          <div className="glass rounded-2xl p-5 shadow-soft">
            <p className="tech-label text-mutext">deployment facts (C1–C3)</p>
            <ul className="mt-3 space-y-2 text-xs leading-relaxed text-mutext">
              <li>• Full pipeline measures ~3–4 s per photo on 2 vCPUs — a CPU container, not serverless.</li>
              <li>• ~30 MB ONNX models — no GPU needed; no heavy PyTorch/TF runtime in production.</li>
              <li>• Offline: the browser keeps only the clearly-labelled colour heuristic.</li>
              <li>• Free web instances sleep after ~15 min idle; cold start 30–60 s.</li>
            </ul>
          </div>
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mt-6 text-center font-mono text-[11px] text-mutext"
        >
          full tables + scopes → <code className="rounded bg-slate-100 px-1.5 py-0.5">vision-api/METRICS.md</code> ·
          served at <code className="rounded bg-slate-100 px-1.5 py-0.5">GET /api/health</code>
        </motion.p>
      </div>
    </section>
  );
}

function MetricCard({
  title,
  subtitle,
  rows,
  scope,
}: {
  title: string;
  subtitle: string;
  rows: Array<[string, string]>;
  scope: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.5 }}
      className="glass flex flex-col rounded-2xl p-5 shadow-soft"
    >
      <p className="text-sm font-extrabold text-fg">{title}</p>
      <p className="mt-1 text-[11px] leading-relaxed text-mutext">{subtitle}</p>
      <div className="mt-4 space-y-1.5">
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-2 border-b border-line/50 pb-1.5">
            <span className="text-xs text-mutext">{k}</span>
            <span className="mono text-sm font-bold text-fg">{v}</span>
          </div>
        ))}
      </div>
      {scope && <p className="mono mt-auto pt-4 text-[10px] leading-relaxed text-mutext/90">scope: {scope}</p>}
    </motion.div>
  );
}
