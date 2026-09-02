import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Hero3D } from './components/Onion3D';
import { ScanStage } from './components/ScanStage';
import { DetectionCanvas } from './components/DetectionCanvas';
import { ResultsDashboard } from './components/ResultsDashboard';
import { InspectionView } from './components/InspectionView';
import { analyzeImage, getEngine, probeHealth } from './services/visionService';
import type { AnalyzeResponse, SourceMode } from './types/vision';

type Stage = 'hero' | 'scan' | 'detecting' | 'results' | 'inspect';

export default function App() {
  const [stage, setStage] = useState<Stage>('hero');
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [sourceMode, setSourceMode] = useState<SourceMode>('upload');
  const [response, setResponse] = useState<AnalyzeResponse | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<{ ok: boolean; text: string } | null>(null);
  const engine = useMemo(() => getEngine(), []);

  useEffect(() => {
    probeHealth().then(setHealth);
  }, []);

  const runAnalysis = async (src: string, mode: SourceMode) => {
    setImageSrc(src);
    setSourceMode(mode);
    setStage('detecting');
    setError(null);
    const img = new Image();
    img.onload = async () => {
      try {
        const out = await analyzeImage(img, mode);
        setResponse(out);
        setSelected(null);
        setStage('results');
      } catch (e) {
        setError(String(e));
        setStage('scan');
      }
    };
    img.onerror = () => {
      setError('could not decode image');
      setStage('scan');
    };
    img.src = src;
  };

  const demo = response?.engine.includes('DEMO') ?? false;

  return (
    <div className="relative flex min-h-full flex-col">
      {/* backdrop */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,#1b1030_0%,#0b0714_55%,#070410_100%)]" />
        <div className="absolute inset-0 opacity-[0.35] [background-image:linear-gradient(#a78bfa11_1px,transparent_1px),linear-gradient(90deg,#a78bfa11_1px,transparent_1px)] [background-size:44px_44px]" />
      </div>

      {/* header */}
      <header className="flex items-center justify-between px-5 py-4 md:px-8">
        <button
          className="flex items-center gap-2.5"
          onClick={() => {
            setStage('hero');
            setResponse(null);
          }}
        >
          <span className="text-xl">🧅</span>
          <span className="text-sm font-bold tracking-widest text-violet-100">
            ONION VISION LAB
          </span>
          <span className="mono hidden rounded bg-white/5 px-1.5 py-0.5 text-[9px] text-violet-200/50 sm:block">
            SIH PS 26031 · prototype
          </span>
        </button>
        <div className="flex items-center gap-2">
          <span
            className={`mono rounded border px-2 py-1 text-[10px] font-bold ${
              demo
                ? 'border-lab-amber/40 bg-lab-amber/10 text-lab-amber'
                : 'border-lab-green/40 bg-lab-green/10 text-lab-green'
            }`}
          >
            {demo ? 'DEMO ENGINE' : 'LIVE'}
          </span>
          <span className="mono hidden rounded border border-lab-line bg-lab-panel px-2 py-1 text-[10px] text-violet-200/60 md:block">
            {health ? (health.ok ? `API ✓ ${health.text}` : 'API unreachable → demo fallback') : 'API …'}
          </span>
        </div>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-10 md:px-8">
        <AnimatePresence mode="wait">
          {stage === 'hero' && (
            <motion.section
              key="hero"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -16 }}
              className="relative grid w-full max-w-5xl items-center gap-8 md:grid-cols-2"
            >
              <Hero3D />
              <div className="relative z-10 md:col-start-1">
                <motion.h1
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-3xl font-extrabold leading-tight md:text-4xl"
                >
                  See every onion.
                  <br />
                  <span className="bg-gradient-to-r from-lab-accent to-fuchsia-300 bg-clip-text text-transparent">
                    Judge only what is visible.
                  </span>
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.15 }}
                  className="mt-4 max-w-md text-sm leading-relaxed text-violet-200/70"
                >
                  Multi-onion detection, a second-stage onion verifier, and a
                  three-signal fused condition ensemble - on photos of onion
                  piles or trays. It reports visible-surface findings and always
                  says what it cannot know: internal quality.
                </motion.p>
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 }}
                  className="mt-6 flex flex-wrap gap-3"
                >
                  <button className="btn-primary" onClick={() => setStage('scan')}>
                    ▶ begin inspection
                  </button>
                  <span className="mono self-center text-[10px] text-violet-200/40">
                    engine: {engine.label}
                  </span>
                </motion.div>
              </div>
            </motion.section>
          )}

          {stage === 'scan' && (
            <motion.section key="scan" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              {error && <p className="mx-auto mb-3 max-w-3xl text-center text-xs text-lab-red">{error}</p>}
              <ScanStage onImage={runAnalysis} busy={false} />
            </motion.section>
          )}

          {stage === 'detecting' && imageSrc && (
            <motion.section key="detecting" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="w-full max-w-3xl">
              <DetectionCanvas imageSrc={imageSrc} stage="detecting" results={[]} onSelect={() => {}} selectedIndex={null} />
              <p className="mono mt-4 text-center text-xs text-lab-accent animate-pulse">
                {sourceMode === 'camera' ? 'analyzing live capture' : 'analyzing image'} · YOLOv8n →
                TF verifier → fused condition ensemble …
              </p>
            </motion.section>
          )}

          {stage === 'results' && response && imageSrc && (
            <motion.section key="results" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="w-full">
              <div className="mx-auto mb-5 max-w-5xl">
                <DetectionCanvas
                  imageSrc={imageSrc}
                  stage="done"
                  results={response.results}
                  selectedIndex={selected}
                  onSelect={(i) => setSelected(i)}
                />
              </div>
              <ResultsDashboard
                response={response}
                imageSrc={imageSrc}
                onInspect={(i) => {
                  setSelected(i);
                  setStage('inspect');
                }}
                onRescan={() => {
                  setStage('scan');
                  setResponse(null);
                }}
              />
            </motion.section>
          )}

          {stage === 'inspect' && response && imageSrc && selected != null && response.results[selected] && (
            <motion.section key="inspect" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="w-full py-4">
              <InspectionView
                result={response.results[selected]}
                onBack={() => setStage('results')}
              />
            </motion.section>
          )}
        </AnimatePresence>
      </main>

      <footer className="mono px-5 pb-4 text-center text-[10px] text-violet-200/35 md:px-8">
        visible-surface analysis only · internal quality cannot be determined by any camera ·
        confidences are visual prediction confidences, never food-safety probabilities ·
        findings vocabulary: discoloration / damage / mold-like / shriveling / sprouting
      </footer>
    </div>
  );
}
