import { motion, useReducedMotion } from 'framer-motion';
import OnionModel from './OnionModel';
import { requestCameraStart } from '../services/cameraBus';

function FloatingSensorCard({
  label,
  value,
  accent = false,
  delay = 0,
  className = '',
}: {
  label: string;
  value: string;
  accent?: boolean;
  delay?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: reduce ? 0 : [0, -8, 0] }}
      transition={{
        opacity: { duration: 0.7, delay },
        y: reduce ? { duration: 0.7, delay } : { duration: 5.5, repeat: Infinity, ease: 'easeInOut', delay },
      }}
      className={`glass rounded-xl px-3.5 py-2.5 shadow-soft ${className}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${accent ? 'bg-electric pulse-dot' : 'bg-emerald-500 pulse-dot'}`} />
        <span className="tech-label text-mutext">{label}</span>
      </div>
      <div className="mt-1 font-mono text-[13px] font-semibold text-fg">{value}</div>
    </motion.div>
  );
}

export default function Hero3D() {
  const goVisionLab = (start: boolean) => {
    document.getElementById('vision-lab')?.scrollIntoView({ behavior: 'smooth' });
    if (start) setTimeout(() => requestCameraStart(), 650);
  };

  return (
    <section id="home" className="relative overflow-hidden pt-28 md:pt-32">
      <div className="dot-grid pointer-events-none absolute inset-0 opacity-60" />
      <div className="pointer-events-none absolute -right-40 top-8 h-[560px] w-[560px] rounded-full bg-electric/10 blur-[130px]" />
      <div className="pointer-events-none absolute -left-32 bottom-0 h-[380px] w-[380px] rounded-full bg-electric2/10 blur-[110px]" />

      <div className="relative mx-auto grid max-w-7xl gap-10 px-5 pb-16 md:grid-cols-[1.05fr_1fr] md:items-center md:px-8">
        {/* text column */}
        <div className="order-2 md:order-1">
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="tech-label text-electric"
          >
            Smart Onion Project / SIH PS 26031
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 22 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
            className="mt-4 font-display text-[2.7rem] font-extrabold leading-[1.04] tracking-tight text-fg sm:text-6xl lg:text-[4.2rem]"
          >
            See every onion.
            <br />
            <span className="text-gradient-blue">Judge only what is visible.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.16 }}
            className="mt-6 max-w-xl text-base leading-relaxed text-mutext md:text-lg"
          >
            Advanced inside — YOLO detection, a TensorFlow verifier gate, a
            PyTorch condition CNN, scikit-learn fusion. Simple outside — point
            the camera, watch the colours, tap once, read the verdict in plain
            language. Made for a mandi worker, a shopkeeper, anyone.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.26 }}
            className="mt-9 flex flex-wrap gap-4"
          >
            <button onClick={() => goVisionLab(true)} className="btn-primary-blue h-12 px-7 text-[15px]">
              ▶ begin inspection
            </button>
            <a
              href="#project"
              className="btn-ghost-light h-12 px-7 text-[15px]"
            >
              Explore project
            </a>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-3"
          >
            {[
              ['DETECTOR', 'YOLOv8n · ONNX'],
              ['VERIFIER', 'TensorFlow gate'],
              ['CONDITION', 'PyTorch + RF + HSV'],
              ['COLOUR CUES', 'on-device, live'],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-electric pulse-dot" />
                <span className="tech-label text-mutext">{k}</span>
                <span className="mono text-xs font-bold text-fg">{v}</span>
              </div>
            ))}
          </motion.div>
        </div>

        {/* 3D onion column */}
        <div className="relative order-1 md:order-2">
          <div className="pointer-events-none absolute inset-0 hidden items-center justify-center md:flex">
            <div className="ring-spin h-[440px] w-[440px] rounded-full border border-electric/20" />
          </div>
          <div className="pointer-events-none absolute inset-0 hidden items-center justify-center md:flex">
            <div className="ring-spin-rev h-[540px] w-[540px] rounded-full border border-dashed border-electric2/25" />
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.15 }}
            className="relative"
          >
            <OnionModel height={480} controls={false} />
            <FloatingSensorCard label="DETECTOR" value="YOLOv8n · READY" accent delay={0.5} className="absolute left-0 top-6 hidden sm:block" />
            <FloatingSensorCard label="VERIFIER GATE" value="TF · τ 0.5" delay={0.8} className="absolute right-0 top-24 hidden sm:block" />
            <FloatingSensorCard label="COLOUR CUES" value="LIVE · 1.2s" accent delay={1.1} className="absolute bottom-24 left-2 hidden md:block" />
            <FloatingSensorCard label="CAMERA" value="ON CLICK ONLY" delay={1.0} className="absolute right-4 top-4" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
