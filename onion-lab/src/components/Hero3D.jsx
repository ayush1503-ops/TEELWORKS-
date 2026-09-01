import React from "react";
import { motion } from "framer-motion";
import OnionModel from "./OnionModel";
import FloatingSensorCard from "./FloatingSensorCard";
import { requestCameraStart } from "../lib/cameraBus";

export default function Hero3D() {
  const goVisionLab = (start) => {
    document.getElementById("vision-lab")?.scrollIntoView({ behavior: "smooth" });
    if (start) setTimeout(() => requestCameraStart(), 650);
  };

  return (
    <section id="home" className="relative overflow-hidden pt-28 md:pt-32">
      {/* backdrop: blue radial glow + dot grid (asymmetric) */}
      <div className="dot-grid pointer-events-none absolute inset-0 opacity-70" />
      <div className="pointer-events-none absolute -right-40 top-10 h-[560px] w-[560px] rounded-full bg-electric/10 blur-[130px]" />
      <div className="pointer-events-none absolute -left-32 bottom-0 h-[380px] w-[380px] rounded-full bg-electric2/10 blur-[110px]" />

      <div className="relative mx-auto grid max-w-7xl gap-10 px-5 pb-16 md:grid-cols-[1.05fr_1fr] md:items-center md:px-8">
        {/* ------------------ text column (asymmetric, left) ------------------ */}
        <div className="order-2 md:order-1">
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="tech-label text-electric"
          >
            Smart Onion Project / 01
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.08 }}
            className="mt-4 font-display text-[2.6rem] leading-[1.05] tracking-tight text-fg sm:text-6xl lg:text-7xl"
          >
            Understand Your <span className="text-gradient-blue">Onion</span>.
            <br />
            Grow It <span className="text-gradient-blue">Smarter</span>.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.18 }}
            className="mt-6 max-w-md text-base leading-relaxed text-mutext md:text-lg"
          >
            An interactive agricultural system designed to observe, analyze and
            understand onion growth using computer vision and smart monitoring.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.28 }}
            className="mt-9 flex flex-wrap gap-4"
          >
            <button
              onClick={() => goVisionLab(true)}
              className="btn-primary-blue flex h-12 items-center gap-2 rounded-xl px-7 font-semibold"
            >
              ◉ Start Camera
            </button>
            <a
              href="#project"
              className="flex h-12 items-center rounded-xl border border-slate-200 bg-white px-7 font-semibold text-fg shadow-soft transition-all hover:-translate-y-0.5 hover:border-electric/40 hover:text-electric"
            >
              Explore Project
            </a>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-10 flex flex-wrap items-center gap-x-8 gap-y-3"
          >
            {[
              ["CV PIPELINE", "LOCAL"],
              ["RENDER", "WEBGL"],
              ["DATA", "ON-DEVICE"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <span className="h-1 w-1 rounded-full bg-electric pulse-dot" />
                <span className="tech-label text-mutext">{k}</span>
                <span className="font-mono text-xs font-bold text-fg">{v}</span>
              </div>
            ))}
          </motion.div>
        </div>

        {/* ------------------ 3D onion column ------------------ */}
        <div className="relative order-1 md:order-2">
          {/* slow rotating rings behind the onion (decorative, desktop) */}
          <div className="pointer-events-none absolute inset-0 hidden items-center justify-center md:flex">
            <div className="ring-spin h-[440px] w-[440px] rounded-full border border-electric/15" />
          </div>
          <div className="pointer-events-none absolute inset-0 hidden items-center justify-center md:flex">
            <div className="ring-spin-rev h-[540px] w-[540px] rounded-full border border-dashed border-electric2/20" />
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.15 }}
            className="relative"
          >
            <OnionModel height={520} className="md:h-[560px]" />

            {/* floating technical UI around the onion */}
            <FloatingSensorCard label="CROP STATUS" value="MONITORING" accent delay={0.5} className="absolute left-0 top-8 hidden sm:block" />
            <FloatingSensorCard label="HEALTH" value="GOOD" delay={0.8} className="absolute right-0 top-24 hidden sm:block" />
            <FloatingSensorCard label="SOIL MOISTURE" value="68% · SAMPLE" accent delay={1.1} className="absolute bottom-24 left-2 hidden md:block" />
            <FloatingSensorCard label="GROWTH STAGE" value="VEGETATIVE" delay={0.65} className="absolute bottom-8 right-4 hidden sm:block" />
            <FloatingSensorCard label="CAMERA READY" value="STANDBY" accent delay={1.0} className="absolute right-6 top-4 sm:right-2" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
