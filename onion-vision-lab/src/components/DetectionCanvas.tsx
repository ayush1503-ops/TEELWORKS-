import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import type { OnionResult, SourceMode } from '../types/vision';

interface Props {
  imageSrc: string;
  stage: 'detecting' | 'done';
  results: OnionResult[];
  onSelect: (index: number) => void;
  selectedIndex: number | null;
  maxHeight?: number;
}

const STROKE: Record<OnionResult['status'], string> = {
  RED: '#DC2626',
  YELLOW: '#D97706',
  GREEN: '#16A34A',
};

export default function DetectionCanvas({ imageSrc, stage, results, onSelect, selectedIndex, maxHeight }: Props) {
  const [box, setBox] = useState<{ w: number; h: number } | null>(null);
  const [sweep, setSweep] = useState(0);

  useEffect(() => {
    if (stage !== 'detecting') return;
    let raf = 0;
    const t0 = performance.now();
    const loop = () => {
      setSweep(((performance.now() - t0) / 1500) % 1);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [stage]);

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-line bg-white shadow-soft">
      <img
        src={imageSrc}
        alt="scan"
        className="block w-full"
        style={maxHeight ? { maxHeight, objectFit: 'contain' } : undefined}
        onLoad={(e) => {
          const el = e.currentTarget;
          setBox({ w: el.naturalWidth, h: el.naturalHeight });
        }}
      />
      {stage === 'detecting' && (
        <motion.div
          className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-electric to-transparent shadow-[0_0_16px_3px_rgba(0,82,255,0.5)]"
          style={{ top: `${sweep * 100}%` }}
        />
      )}
      {stage === 'done' &&
        box &&
        results.map((r, i) => {
          const stroke = STROKE[r.status];
          return (
            <motion.button
              key={r.id}
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.05, type: 'spring', stiffness: 260, damping: 20 }}
              onClick={() => onSelect(i)}
              aria-label={`${r.id} ${r.statusLabel}`}
              className={`absolute border-2 transition ${
                selectedIndex === i ? 'bg-electric/10' : 'hover:bg-white/20'
              }`}
              style={{
                left: `${r.bbox.x * 100}%`,
                top: `${r.bbox.y * 100}%`,
                width: `${r.bbox.width * 100}%`,
                height: `${r.bbox.height * 100}%`,
                borderColor: stroke,
                boxShadow: `0 0 0 1px rgba(255,255,255,0.9), 0 0 14px ${stroke}66`,
                borderRadius: '999px',
              }}
            >
              <span
                className="mono absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border px-1.5 py-0.5 text-[10px] font-bold shadow-sm"
                style={{ background: '#fff', color: stroke, borderColor: stroke }}
              >
                {r.id.replace('onion-', '#')} · {(r.confidence * 100).toFixed(0)}%
              </span>
            </motion.button>
          );
        })}
      {stage === 'detecting' && (
        <div className="mono absolute bottom-3 left-3 rounded-lg border border-electric/30 bg-white/95 px-3 py-1.5 text-xs font-semibold text-electric shadow-soft">
          detecting onions · letterbox 320 · conf 0.45 …
        </div>
      )}
    </div>
  );
}

export function sourceModeLabel(mode: SourceMode): string {
  return mode === 'camera' ? 'LIVE CAMERA' : mode === 'demo' ? 'SAMPLE PHOTO' : 'UPLOAD';
}
