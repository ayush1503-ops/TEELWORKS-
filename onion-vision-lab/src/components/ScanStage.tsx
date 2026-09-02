import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import type { SourceMode } from '../types/vision';

interface Props {
  onImage: (src: string, mode: SourceMode) => void;
  busy: boolean;
}

const DEMO_SRC = '/scan_demo_52_onions.jpg';

export function ScanStage({ onImage, busy }: Props) {
  const [drag, setDrag] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [camError, setCamError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // camera is ONLY touched after a user click - never on load
  const startCamera = async () => {
    setCamError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOn(true);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch (e) {
      setCamError(`camera unavailable: ${String(e).slice(0, 90)}`);
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraOn(false);
  };

  useEffect(() => () => stopCamera(), []);

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
    <div className="mx-auto w-full max-w-3xl">
      <div
        className={`panel relative flex min-h-[300px] flex-col items-center justify-center gap-5 border-2 border-dashed p-8 transition ${
          drag ? 'border-lab-accent bg-lab-accent/10' : 'border-lab-line'
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
            <video ref={videoRef} playsInline muted className="w-full rounded-xl border border-lab-line" />
            <div className="mt-3 flex items-center justify-between">
              <span className="mono rounded bg-lab-green/15 px-2 py-1 text-[10px] font-bold text-lab-green">
                LIVE · frames processed in-memory for this analysis only, never stored
              </span>
              <div className="flex gap-2">
                <button className="btn-ghost" onClick={stopCamera}>
                  stop
                </button>
                <button className="btn-primary" onClick={capture} disabled={busy}>
                  capture &amp; analyze
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center"
            >
              <div className="text-4xl">🧅</div>
              <h2 className="mt-3 text-lg font-semibold">Scan onions</h2>
              <p className="mt-1 max-w-md text-sm text-violet-200/60">
                One photo of loose onions or a tray. Detection, verification and
                visible-condition analysis run on the image you provide - visible
                surface only.
              </p>
            </motion.div>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button className="btn-primary" disabled={busy} onClick={startCamera}>
                📷 use camera <span className="mono ml-1 text-[10px] opacity-70">(click = permission)</span>
              </button>
              <button className="btn-ghost" disabled={busy} onClick={() => fileRef.current?.click()}>
                ⬆ upload photo
              </button>
              <button
                className="btn-ghost"
                disabled={busy}
                onClick={() => {
                  fetch(DEMO_SRC)
                    .then((r) => (r.ok ? r.blob() : Promise.reject(new Error('sample missing'))))
                    .then((b) => readFile(new File([b], 'scan_demo_52_onions.jpg', { type: 'image/jpeg' }), 'demo'))
                    .catch(() => setCamError('sample photo unavailable - upload your own'));
                }}
              >
                🖼 sample tray photo (52)
              </button>
            </div>
            {camError && <p className="text-xs text-lab-red">{camError}</p>}
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
      <p className="mono mt-4 text-center text-[11px] text-violet-200/40">
        frames are analyzed in-memory for this call and are not uploaded or stored beyond it ·
        camera permission requested only on click
      </p>
    </div>
  );
}
