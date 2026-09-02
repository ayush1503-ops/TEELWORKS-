import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import type { OnionResult, SourceMode } from '../types/vision';

interface Props {
  imageSrc: string;
  stage: 'detecting' | 'done';
  results: OnionResult[];
  onSelect: (index: number) => void;
  selectedIndex: number | null;
}

export function DetectionCanvas({ imageSrc, stage, results, onSelect, selectedIndex }: Props) {
  const [box, setBox] = useState<{ w: number; h: number } | null>(null);
  const [sweep, setSweep] = useState(0);

  useEffect(() => {
    if (stage !== 'detecting') return;
    let raf = 0;
    const t0 = performance.now();
    const loop = () => {
      setSweep(((performance.now() - t0) / 1600) % 1);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [stage]);

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-lab-line bg-black/40">
      <img
        src={imageSrc}
        alt="scan"
        className="block w-full"
        onLoad={(e) => {
          const el = e.currentTarget;
          setBox({ w: el.naturalWidth, h: el.naturalHeight });
        }}
      />
      {stage === 'detecting' && (
        <motion.div
          className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-lab-accent to-transparent shadow-[0_0_18px_4px_rgba(167,139,250,0.45)]"
          style={{ top: `${sweep * 100}%` }}
        />
      )}
      {stage === 'done' &&
        box &&
        results.map((r, i) => {
          const stroke =
            r.status === 'RED' ? '#f87171' : r.status === 'YELLOW' ? '#fbbf24' : '#34d399';
          return (
            <motion.button
              key={r.id}
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.06, type: 'spring', stiffness: 260, damping: 20 }}
              onClick={() => onSelect(i)}
              className={`absolute border-2 transition ${
                selectedIndex === i ? 'bg-white/10' : 'hover:bg-white/5'
              }`}
              style={{
                left: `${r.bbox.x * 100}%`,
                top: `${r.bbox.y * 100}%`,
                width: `${r.bbox.width * 100}%`,
                height: `${r.bbox.height * 100}%`,
                borderColor: stroke,
                boxShadow: `0 0 0 1px rgba(0,0,0,0.35), 0 0 16px ${stroke}55`,
                borderRadius: '999px',
              }}
              aria-label={`${r.id} ${r.statusLabel}`}
            >
              <span
                className="mono absolute -top-5 left-2 whitespace-nowrap rounded px-1.5 py-0.5 text-[10px] font-bold"
                style={{ background: `${stroke}22`, color: stroke }}
              >
                {r.id.replace('onion-', '#')} · {(r.confidence * 100).toFixed(0)}%
              </span>
            </motion.button>
          );
        })}
      {stage === 'detecting' && (
        <div className="mono absolute bottom-3 left-3 rounded-lg bg-black/60 px-3 py-1.5 text-xs text-lab-accent">
          detecting onions · letterbox 320 · conf 0.45 …
        </div>
      )}
    </div>
  );
}

export function sourceModeLabel(mode: SourceMode): string {
  return mode === 'camera' ? 'LIVE CAMERA' : mode === 'demo' ? 'SAMPLE PHOTO' : 'UPLOAD';
}
