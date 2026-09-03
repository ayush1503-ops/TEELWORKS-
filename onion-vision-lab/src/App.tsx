import { useEffect, useMemo, useState } from 'react';
import type { AnalyzeResponse, SourceMode } from './types/vision';
import { analyzeImage, getEngine, probeHealth } from './services/visionService';
import Navbar from './components/Navbar';
import Hero3D from './components/Hero3D';
import ProjectStory from './components/ProjectStory';
import HowItWorks from './components/HowItWorks';
import VisionLab from './components/VisionLab';
import OnionExplorer from './components/OnionExplorer';
import ProjectDashboard from './components/ProjectDashboard';
import Footer from './components/Footer';

export default function App() {
  const [response, setResponse] = useState<AnalyzeResponse | null>(null);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [sourceMode, setSourceMode] = useState<SourceMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [health, setHealth] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const engine = useMemo(() => getEngine(), []);
  const demoEngine = (response?.engine.includes('DEMO') ?? false) || !engine.live;

  useEffect(() => {
    probeHealth().then(setHealth);
  }, []);

  const runAnalysis = async (src: string, mode: SourceMode) => {
    setBusy(true);
    setError(null);
    setResponse(null);
    setSelected(null);
    const img = new Image();
    img.onload = async () => {
      // show the "detecting" preview while the API works
      setImageSrc(src);
      setSourceMode(mode);
      requestAnimationFrame(() => {
        document.getElementById('vision-lab')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
      try {
        const out = await analyzeImage(img, mode);
        setResponse(out);
      } catch (e) {
        setError(String(e));
        setResponse(null);
      } finally {
        setBusy(false);
      }
    };
    img.onerror = () => {
      setError('could not decode the image — try another photo');
      setImageSrc(null);
      setSourceMode(null);
      setBusy(false);
    };
    img.src = src;
  };

  const newScan = () => {
    setResponse(null);
    setImageSrc(null);
    setSourceMode(null);
    setSelected(null);
    setError(null);
    requestAnimationFrame(() => {
      document.getElementById('vision-lab')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  const goInspect = (i: number) => {
    setSelected(i);
    document.getElementById('explorer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const backToResults = () => {
    setSelected(null);
    document.getElementById('vision-lab')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-bg text-fg">
      <Navbar demoEngine={demoEngine} health={health} />
      <main>
        <Hero3D />
        <ProjectStory />
        <HowItWorks />
        <VisionLab
          response={response}
          busy={busy}
          imageSrc={imageSrc}
          sourceMode={sourceMode}
          error={error}
          onImage={runAnalysis}
          onNewScan={newScan}
          onInspect={goInspect}
        />
        <OnionExplorer
          response={response}
          imageSrc={imageSrc}
          selected={selected}
          onSelect={(i) => setSelected(i)}
          onBackToResults={backToResults}
        />
        <ProjectDashboard />
      </main>
      <Footer />
    </div>
  );
}
