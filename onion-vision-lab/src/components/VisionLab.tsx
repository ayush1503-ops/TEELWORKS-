import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { AnalyzeResponse, SourceMode } from '../types/vision';
import { colorScanFrame, type ColorScanResult } from '../services/liveColorScan';
import { cameraBus } from '../services/cameraBus';
import { VARIETY_LABEL } from '../types/vision';
import DetectionCanvas from './DetectionCanvas';
import ResultsDashboard from './ResultsDashboard';

const DEMO_SRC = '/scan_demo_52_onions.jpg';
const SCAN_MS = 1200; // ~1 frame/1.2s on a 320px canvas (F3)
const VERDICT_HEX: Record<string, string> = {
  'FRESH-LOOKING COLORS': '#16A34A',
  'SUSPECT DARK AREAS': '#D97706',
  'STRONG DARK/SPORE COLORS': '#DC2626',
};

interface VisionLabProps {
  response: AnalyzeResponse | null;
  busy: boolean;
  imageSrc: string | null;
  sourceMode: SourceMode | null;
  error: string | null;
  onImage: (src: string, mode: SourceMode) => void;
  onNewScan: () => void;
  onInspect: (index: number) => void;
}

export default function VisionLab(props: VisionLabProps) {
  const { response, busy, imageSrc, error, onImage, onNewScan, onInspect } = props;

  if (imageSrc) {
    return (
      <section id="vision-lab" className="relative scroll-mt-20 py-20 md:py-24">
        <div className="mx-auto w-full max-w-6xl px-5 md:px-8">
          {response === null ? (
            <>
              <DetectionCanvas imageSrc={imageSrc} stage="detecting" results={[]} onSelect={() => {}} selectedIndex={null} />
              <p className="mono mt-5 text-center text-xs font-semibold text-electric animate-pulse">
                analyzing · YOLOv8n → TF verifier → fused condition ensemble (CNN + RF + HSV) …
              </p>
            </>
          ) : (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
              <div className="mx-auto mb-5 max-w-4xl">
                <DetectionCanvas
                  imageSrc={imageSrc}
                  stage="done"
                  results={response.results}
                  selectedIndex={null}
                  onSelect={() => {}}
                />
              </div>
              <ResultsDashboard response={response} imageSrc={imageSrc} onInspect={onInspect} onRescan={onNewScan} />
            </motion.div>
          )}
        </div>
      </section>
    );
  }

  return (
    <section id="vision-lab" className="relative scroll-mt-20 overflow-hidden bg-[#F7F9FF] py-20 md:py-24">
      <div className="dot-grid-soft pointer-events-none absolute inset-0" />
      <div className="relative mx-auto max-w-6xl px-5 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="tech-label text-electric">Vision Lab / the scanner</p>
            <h2 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-fg md:text-5xl">
              Camera → colours → <span className="text-gradient-blue">verdict</span>
            </h2>
          </div>
          <p className="max-w-sm text-sm leading-relaxed text-mutext">
            Point the camera and the colours update live. Tap once and the full
            model stack takes over. Camera permission is requested only on click;
            frames stay in memory.
          </p>
        </div>

        <ScanCard
          error={error}
          busy={busy}
          onImage={onImage}
          onDemo={() => {
            fetch(DEMO_SRC)
              .then((r) => (r.ok ? r.blob() : Promise.reject(new Error('sample missing'))))
              .then((b) => onImage(URL.createObjectURL(b), 'demo'))
              .catch(() => onImage(DEMO_SRC, 'demo'));
          }}
        />
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */

function ScanCard({
  error,
  busy,
  onImage,
  onDemo,
}: {
  error: string | null;
  busy: boolean;
  onImage: (src: string, mode: SourceMode) => void;
  onDemo: () => void;
}) {
  const [drag, setDrag] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [camError, setCamError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // camera bus: "Launch Camera" anywhere in the page starts the live scanner
  useEffect(() => {
    const onStart = () => {
      const el = document.getElementById('vision-lab');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
      setTimeout(() => startCamera().catch(() => {}), 600);
    };
    cameraBus.addEventListener('start', onStart);
    return () => cameraBus.removeEventListener('start', onStart);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // stop camera on unmount
  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    },
    [],
  );

  const drawOverlay = (): ColorScanResult | null => {
    const v = videoRef.current;
    const c = overlayRef.current;
    if (!v || !c || v.videoWidth === 0) return null;
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    const ctx = c.getContext('2d');
    if (!ctx) return null;
    ctx.clearRect(0, 0, c.width, c.height);
    const scan = colorScanFrame(v); // in-memory sample, <=320px internally
    const w = c.width;
    const h = c.height;
    for (const b of scan.blobs) {
      const hex = VERDICT_HEX[b.verdict];
      ctx.strokeStyle = hex;
      ctx.lineWidth = Math.max(2, w * 0.004);
      ctx.setLineDash([8, 6]);
      ctx.strokeRect(b.x * w, b.y * h, b.width * w, b.height * h);
      ctx.setLineDash([]);
      ctx.font = `600 ${Math.max(11, Math.round(w * 0.016))}px ui-monospace, monospace`;
      const label = `${b.verdict}  ·  dark ${(b.darkPct * 100).toFixed(1)}%  ·  mould ${(b.moldPct * 100).toFixed(1)}%  ·  sprout ${(b.sproutPct * 100).toFixed(1)}%`;
      ctx.fillStyle = 'rgba(15,23,42,0.85)';
      const tw = ctx.measureText(label).width + 12;
      const ty = Math.max(2, b.y * h - 22);
      ctx.fillRect(b.x * w, ty, tw, 18);
      ctx.fillStyle = hex;
      ctx.fillText(label, b.x * w + 6, ty + 13);
    }
    return scan;
  };

  const startCamera = async () => {
    setCamError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setCamError('camera API unsupported on this device/browser');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOn(true);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
    } catch (e) {
      setCamError(`camera unavailable: ${String(e).slice(0, 110)}`);
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraOn(false);
  };

  const capture = () => {
    const v = videoRef.current;
    if (!v) return;
    const c = document.createElement('canvas');
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext('2d')?.drawImage(v, 0, 0);
    stopCamera();
    onImage(c.toDataURL('image/jpeg', 0.92), 'camera');
  };

  const readFile = (file: File, mode: SourceMode = 'upload') => {
    const rd = new FileReader();
    rd.onload = () => onImage(String(rd.result), mode);
    rd.readAsDataURL(file);
  };

  return (
    <div className="mx-auto mt-10 w-full max-w-4xl">
      <div
        className={`glass relative flex min-h-[320px] flex-col items-center justify-center gap-5 rounded-3xl border-2 border-dashed p-6 shadow-soft md:p-8 ${
          drag ? 'border-electric bg-electricSoft' : 'border-line'
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f && f.type.startsWith('image/')) readFile(f);
        }}
      >
        {cameraOn ? (
          <div className="w-full">
            <div className="scanlines relative overflow-hidden rounded-2xl border border-line bg-black">
              <video ref={videoRef} playsInline muted className="block w-full" style={{ maxHeight: 420, objectFit: 'contain' }} />
              <canvas ref={overlayRef} className="pointer-events-none absolute inset-0 h-full w-full" />
            </div>
            <LiveHeuristicLoop videoRef={videoRef} draw={drawOverlay} active={cameraOn} />
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <span className="tech-label rounded-full bg-amberSoft px-3 py-1.5 text-amber">
                colour heuristic — not the AI model; capture for the full verdict
              </span>
              <div className="flex gap-2">
                <button className="btn-ghost-light h-10 px-5 text-sm" onClick={stopCamera}>
                  stop camera
                </button>
                <button className="btn-primary-blue h-10 px-6 text-sm" onClick={capture} disabled={busy}>
                  capture for full verdict
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-center">
              <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-electricSoft text-3xl shadow-soft">🧅</div>
              <h3 className="mt-4 text-2xl font-extrabold text-fg">Scan onions</h3>
              <p className="mx-auto mt-1.5 max-w-lg text-sm leading-relaxed text-mutext">
                One photo of loose onions or a tray — or just point the camera
                and watch the live colour preview below. Detection, verification
                and visible-condition analysis run on the image you provide.
              </p>
            </motion.div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button className="btn-primary-blue h-11 px-6 text-sm" onClick={startCamera} disabled={busy}>
                📷 use camera <span className="mono ml-1 text-[10px] opacity-80">(click = permission)</span>
              </button>
              <button className="btn-ghost-light h-11 px-5 text-sm" onClick={() => fileRef.current?.click()} disabled={busy}>
                ⬆ upload photo
              </button>
              <button className="btn-ghost-light h-11 px-5 text-sm" onClick={onDemo} disabled={busy}>
                🖼 sample tray photo (52)
              </button>
            </div>
            {(error || camError) && <p className="max-w-md text-center text-xs font-medium text-red">{error ?? camError}</p>}
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) readFile(f);
                e.target.value = '';
              }}
            />
          </>
        )}
      </div>
      <div className="mt-4 flex flex-col items-center gap-1.5">
        <p className="mono text-center text-[11px] leading-relaxed text-mutext">
          colour heuristic runs ~1 frame / 1.2 s on a 320px canvas, fully in-memory · frames are never uploaded
          or stored beyond the single analysis you trigger
        </p>
        <VarietyLegend />
      </div>
    </div>
  );
}

/** runs the F3 live heuristic loop while the camera is active */
function LiveHeuristicLoop({
  videoRef,
  draw,
  active,
}: {
  videoRef: React.RefObject<HTMLVideoElement>;
  draw: () => ColorScanResult | null;
  active: boolean;
}) {
  const [summary, setSummary] = useState<string | null>(null);
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!active) return;
    let alive = true;
    const id = window.setInterval(() => {
      const v = videoRef.current;
      if (!v || v.readyState < 2) return;
      const scan = draw();
      if (scan && scan.blobs.length > 0) {
        const worst = scan.blobs.reduce((a, b) =>
          b.verdict === 'STRONG DARK/SPORE COLORS' || (b.verdict === 'SUSPECT DARK AREAS' && a.verdict === 'FRESH-LOOKING COLORS') ? b : a,
        );
        const isPlural = scan.blobs.length > 1;
        setSummary(
          `${scan.blobs.length} onion-like region${isPlural ? 's' : ''} · ${worst.verdict.toLowerCase()} seen (dark ${(worst.darkPct * 100).toFixed(1)}%, mould ${(worst.moldPct * 100).toFixed(1)}%, sprout ${(worst.sproutPct * 100).toFixed(1)}%) · ${VARIETY_LABEL[worst.variety].toLowerCase()} estimate`,
        );
      } else {
        setSummary('no onion-like colours in view yet — move the camera closer');
      }
      if (alive) setTick((t) => t + 1);
    }, SCAN_MS);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  return (
    <AnimatePresence>
      {summary && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="mt-2 text-center text-xs font-medium leading-relaxed text-mutext"
        >
          live colour preview · {summary}
        </motion.p>
      )}
    </AnimatePresence>
  );
}

function VarietyLegend() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
      {(
        [
          ['#B91C1C', 'red'],
          ['#B45309', 'golden / yellow'],
          ['#7C3AED', 'purple / violet'],
          ['#E2E8F0', 'white / cream'],
        ] as Array<[string, string]>
      ).map(([hex, label]) => (
        <span key={label} className="mono flex items-center gap-1.5 text-[10px] text-mutext">
          <span className="h-2.5 w-2.5 rounded-full border border-black/10" style={{ background: hex }} />
          {label} <span className="opacity-70">(estimate — never ground truth)</span>
        </span>
      ))}
    </div>
  );
}
