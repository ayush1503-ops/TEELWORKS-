import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import OnionModel from "./OnionModel";

/* Hotspots are HTML overlays positioned around the 3D onion; the info card
   opens in a side panel so it never covers the model. */

const HOTSPOTS = [
  {
    id: "bulb", label: "Bulb", pos: "left-[6%] top-[52%]",
    title: "Bulb",
    body: "The storage organ the whole crop is grown for. Size, firmness and uniformity of bulbs are what grading and market value depend on.",
    tag: "STRUCTURE",
  },
  {
    id: "skin", label: "Skin", pos: "right-[8%] top-[30%]",
    title: "Outer Skin",
    body: "The papery protective layers. Colour and intactness of the skin are visible quality signals a camera can genuinely observe.",
    tag: "SURFACE",
  },
  {
    id: "roots", label: "Roots", pos: "left-[16%] bottom-[10%]",
    title: "Roots",
    body: "A healthy basal plate with dry roots indicates proper curing. Root development reflects soil and moisture conditions during growth.",
    tag: "BASE",
  },
  {
    id: "leaves", label: "Leaves", pos: "right-[18%] top-[6%]",
    title: "Leaves",
    body: "Leaf colour and tipping are early indicators of crop health — many diseases announce themselves on the leaves first.",
    tag: "TOP GROWTH",
  },
  {
    id: "growth", label: "Growth Area", pos: "right-[30%] bottom-[6%]",
    title: "Growth Area (Neck)",
    body: "The neck closes and dries as the bulb matures. Thickness of the neck is related to storage life and sprouting tendency.",
    tag: "DEVELOPMENT",
  },
];

export default function OnionExplorer() {
  const [active, setActive] = useState(null);

  return (
    <section id="explorer" className="relative scroll-mt-20 overflow-hidden py-24 md:py-32">
      <div className="pointer-events-none absolute right-0 top-24 h-[420px] w-[420px] rounded-full bg-electric/8 blur-[120px]" />
      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="tech-label text-electric"
        >
          3D Explorer
        </motion.p>
        <motion.h2
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.08 }}
          className="mt-3 font-display text-4xl tracking-tight md:text-5xl"
        >
          Explore the <span className="text-gradient-blue">Onion</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.18 }}
          className="mt-4 max-w-lg text-sm leading-relaxed text-mutext"
        >
          Drag to rotate, scroll to zoom. Tap a hotspot to learn what each part of
          the plant tells a grower.
        </motion.p>

        <div className="mt-10 grid items-center gap-8 lg:grid-cols-[1.4fr_1fr]">
          {/* 3D stage with hotspots */}
          <div className="relative rounded-3xl border border-slate-100 bg-gradient-to-b from-white to-muted/60 p-2 shadow-soft">
            <OnionModel height={520} />
            {HOTSPOTS.map((h, i) => (
              <button
                key={h.id}
                onClick={() => setActive(active?.id === h.id ? null : h)}
                className={`absolute z-20 flex items-center gap-2 rounded-full border px-3.5 py-2 backdrop-blur-md transition-all duration-300 ${h.pos} ${
                  active?.id === h.id
                    ? "border-electric bg-electric text-white shadow-glow"
                    : "border-slate-200 bg-white/85 text-fg hover:border-electric/50 hover:text-electric"
                }`}
                style={{ animation: `floaty 5s ease-in-out ${i * 0.7}s infinite` }}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${active?.id === h.id ? "bg-white" : "bg-electric pulse-dot"}`} />
                <span className="tech-label">{h.label}</span>
              </button>
            ))}
            <style>{`@keyframes floaty { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-6px) } }
              @media (prefers-reduced-motion: reduce) { [style*="floaty"] { animation: none !important } }`}</style>
          </div>

          {/* info panel (never covers the 3D object) */}
          <div className="min-h-[220px]">
            <AnimatePresence mode="wait">
              {active ? (
                <motion.div
                  key={active.id}
                  initial={{ opacity: 0, x: 24 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{ duration: 0.28 }}
                  className="rounded-2xl border border-slate-100 bg-white p-7 shadow-lift"
                >
                  <div className="flex items-center justify-between">
                    <span className="tech-label rounded-full bg-electric/10 px-3 py-1 text-electric">
                      {active.tag}
                    </span>
                    <span className="h-2 w-2 rounded-full bg-electric pulse-dot" />
                  </div>
                  <h3 className="mt-5 font-display text-2xl tracking-tight">{active.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-mutext">{active.body}</p>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-full min-h-[220px] items-center justify-center rounded-2xl border border-dashed border-slate-200 p-7"
                >
                  <p className="tech-label text-mutext">Select a hotspot →</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
