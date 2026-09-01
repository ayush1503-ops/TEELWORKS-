import React from "react";
import { motion } from "framer-motion";

const STEPS = [
  ["01", "Camera", "Capture visual information from the field or the lab with any device camera."],
  ["02", "Analysis", "Process the captured frames locally — colour, shape and texture signals."],
  ["03", "Identification", "Identify visible crop characteristics and surface features."],
  ["04", "Insight", "Present the information in a form a grower can actually act on."],
];

export default function HowItWorks() {
  return (
    <section id="how" className="relative scroll-mt-20 overflow-hidden py-24 md:py-32">
      <div className="dot-grid pointer-events-none absolute inset-0 opacity-50" />
      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="tech-label text-electric"
            >
              How It Works
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.08 }}
              className="mt-3 font-display text-4xl tracking-tight md:text-5xl"
            >
              From Frame to <span className="text-gradient-blue">Understanding</span>
            </motion.h2>
          </div>
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="max-w-sm text-sm leading-relaxed text-mutext"
          >
            A four-stage pipeline that keeps every step inspectable — designed as a
            learning system, not a black box.
          </motion.p>
        </div>

        {/* timeline */}
        <div className="relative mt-16">
          {/* connector line — horizontal on desktop, vertical on mobile */}
          <motion.div
            initial={{ scaleX: 0, scaleY: 0 }}
            whileInView={{ scaleX: 1, scaleY: 1 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 1.1, ease: "easeOut" }}
            className="absolute left-[27px] top-0 h-full w-px origin-top bg-gradient-to-b from-electric/60 via-electric/25 to-transparent md:left-0 md:right-0 md:top-[27px] md:h-px md:w-full md:origin-left md:bg-gradient-to-r"
          />

          <div className="grid gap-10 md:grid-cols-4 md:gap-6">
            {STEPS.map(([num, title, body], i) => (
              <motion.div
                key={num}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.55, delay: 0.15 + i * 0.18 }}
                className="relative flex gap-5 md:block"
              >
                {/* glowing node */}
                <div className="relative z-10 grid h-14 w-14 shrink-0 place-items-center rounded-full border border-electric/30 bg-white font-mono text-sm font-bold text-electric shadow-glow">
                  <span className="absolute inset-0 rounded-full bg-electric/10 blur-md" />
                  <span className="relative">{num}</span>
                </div>
                <div className="md:mt-6">
                  <h3 className="font-mono text-sm font-bold uppercase tracking-[0.16em] text-fg">
                    {title}
                  </h3>
                  <p className="mt-2 max-w-xs text-sm leading-relaxed text-mutext">{body}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
