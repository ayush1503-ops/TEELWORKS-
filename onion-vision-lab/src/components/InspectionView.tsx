import { motion } from 'framer-motion';
import { Inspection3D } from './Onion3D';
import type { OnionResult } from '../types/vision';
import { STATUS_COLORS, STATUS_DOT } from '../types/vision';

interface Props {
  result: OnionResult;
  onBack: () => void;
}

export function InspectionView({ result, onBack }: Props) {
  const hasRegions = result.regions.length > 0;
  return (
    <div className="mx-auto grid w-full max-w-5xl gap-5 md:grid-cols-2">
      <div className="panel relative min-h-[380px] overflow-hidden">
        <Inspection3D status={result.status} regions={result.regions} />
        <div className="pointer-events-none absolute left-3 top-3">
          <div className="mono rounded bg-black/50 px-2 py-1 text-[10px] text-violet-200/70">
            3D inspection · visible-surface model
          </div>
        </div>
        <div className="pointer-events-none absolute bottom-3 left-3 right-3">
          {hasRegions ? (
            <div className="mono rounded bg-black/55 px-2.5 py-1.5 text-[10px] leading-relaxed text-lab-red/90">
              ● AI-INFERRED REGION{' '}
              {result.regions.length > 1 ? `(+${result.regions.length - 1} more)` : ''} - suspected
              damage location inferred from image cues, not a measured internal defect
            </div>
          ) : (
            <div className="mono rounded bg-black/55 px-2.5 py-1.5 text-[10px] text-lab-green/80">
              no suspected regions flagged on the visible surface
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        <div className={`panel p-5 ${STATUS_COLORS[result.status]}`}>
          <div className="flex items-center gap-2">
            <span className={`h-3 w-3 rounded-full ${STATUS_DOT[result.status]}`} />
            <h2 className="text-lg font-bold tracking-wide">{result.statusLabel}</h2>
          </div>
          <p className="mono mt-2 text-xs opacity-70">
            {result.id} · visual prediction confidence {(result.confidence * 100).toFixed(0)}% (not a
            food-safety probability)
          </p>
        </div>

        <div className="panel p-5">
          <h3 className="text-sm font-semibold">Why was this flagged?</h3>
          {result.findings.length === 0 ? (
            <p className="mt-2 text-xs text-violet-200/60">
              No damage cues exceeded the review threshold on the visible surface. This is NOT a
              certificate of internal quality - a camera cannot see inside an onion.
            </p>
          ) : (
            <ul className="mt-3 space-y-3">
              {result.findings.map((f, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="rounded-lg border border-lab-line bg-black/25 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold">{f.kind}</span>
                    <span className="mono text-[10px] text-lab-amber">
                      {(f.confidence * 100).toFixed(0)}% visual evidence
                    </span>
                  </div>
                  <p className="mt-1.5 text-xs leading-relaxed text-violet-200/70">{f.evidence}</p>
                </motion.li>
              ))}
            </ul>
          )}
        </div>

        <div className="panel p-5">
          <h3 className="text-sm font-semibold">Measured cues</h3>
          <div className="mono mt-3 grid grid-cols-2 gap-2 text-[11px] text-violet-200/70">
            <CueRow k="darkRatio" v={result.metrics.darkRatio.toFixed(4)} />
            <CueRow k="saturationStd" v={result.metrics.saturationStd.toFixed(1)} />
            <CueRow k="greenTop" v={result.metrics.greenTop.toFixed(4)} />
            <CueRow k="detector conf" v={result.metrics.detectorConfidence.toFixed(3)} />
            {result.metrics.verifierConfidence != null && (
              <CueRow k="verifier p(onion)" v={result.metrics.verifierConfidence.toFixed(3)} />
            )}
            <CueRow k="model" v={result.modelName.split(' + ')[0]} />
          </div>
        </div>

        <button className="btn-ghost w-full" onClick={onBack}>
          ← back to results
        </button>
      </div>
    </div>
  );
}

function CueRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between rounded bg-black/20 px-2.5 py-1.5">
      <span className="text-violet-200/50">{k}</span>
      <span>{v}</span>
    </div>
  );
}
