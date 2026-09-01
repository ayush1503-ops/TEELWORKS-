import React from "react";
import { motion } from "framer-motion";
import CameraScanner from "./CameraScanner";
import OnionModel from "./OnionModel";

export default function VisionLab() {
  return (
    <section id="vision-lab" className="relative scroll-mt-20 overflow-hidden bg-dark py-24 text-white md:py-32">
      <div className="dot-grid-light pointer-events-none absolute inset-0" />
      <div className="pointer-events-none absolute left-1/2 top-1/3 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-electric/15 blur-[150px]" />

      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="tech-label text-electric2"
            >
              Vision Lab / 02
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.08 }}
              className="mt-3 font-display text-4xl tracking-tight md:text-5xl"
            >
              Camera → Vision → <span className="text-gradient-blue">Onion Analysis</span>
            </motion.h2>
          </div>
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="max-w-sm text-sm leading-relaxed text-slate-400"
          >
            The live feed on the left is connected to the model on the right — a
            demonstration of the capture-to-analysis loop. All processing stays
            in your browser.
          </motion.p>
        </div>

        <div className="relative mt-14 grid items-center gap-10 lg:grid-cols-2">
          {/* left: live camera */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6 }}
          >
            <CameraScanner />
          </motion.div>

          {/* connector: animated data line between the two (desktop only) */}
          <div className="pointer-events-none absolute left-1/2 top-1/2 hidden h-24 w-32 -translate-x-1/2 -translate-y-1/2 lg:block">
            <svg viewBox="0 0 128 96" fill="none" className="h-full w-full">
              <motion.path
                d="M0 48 C 40 48, 44 20, 64 20 S 92 60, 128 48"
                stroke="url(#lgrad)"
                strokeWidth="1.5"
                strokeDasharray="5 7"
                animate={{ strokeDashoffset: [0, -48] }}
                transition={{ duration: 2.2, repeat: Infinity, ease: "linear" }}
              />
              <defs>
                <linearGradient id="lgrad" x1="0" x2="128">
                  <stop stopColor="#0052FF" stopOpacity="0.2" />
                  <stop offset="0.5" stopColor="#4D7CFF" />
                  <stop offset="1" stopColor="#0052FF" stopOpacity="0.2" />
                </linearGradient>
              </defs>
            </svg>
            <motion.span
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-electric px-2.5 py-1 text-[9px] font-bold tracking-[0.18em] text-white shadow-glow"
              animate={{ scale: [1, 1.08, 1], opacity: [0.85, 1, 0.85] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              VISION LINK
            </motion.span>
          </div>

          {/* right: the 3D onion under analysis */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="relative rounded-3xl border border-white/10 bg-white/[0.03] p-2"
          >
            <div className="pointer-events-none absolute inset-0 rounded-3xl ring-1 ring-inset ring-electric/20" />
            <OnionModel height={480} />
            <div className="pointer-events-none absolute left-5 top-5">
              <p className="tech-label text-electric2">3D Reference Model</p>
              <p className="mt-1 font-mono text-xs text-slate-400">procedural · webgl · local</p>
            </div>
            <div className="pointer-events-none absolute bottom-5 right-5 rounded-md bg-black/40 px-2.5 py-1 backdrop-blur-sm">
              <span className="tech-label text-amber-300">Demo overlay — detection not connected</span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
