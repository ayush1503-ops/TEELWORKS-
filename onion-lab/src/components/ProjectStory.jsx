import React from "react";
import { motion } from "framer-motion";

const fade = {
  initial: { opacity: 0, y: 30 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
};

export default function ProjectStory() {
  return (
    <section id="project" className="relative scroll-mt-20 overflow-hidden bg-dark py-24 text-white md:py-32">
      {/* texture: dot grid + blue radial glow, asymmetric */}
      <div className="dot-grid-light pointer-events-none absolute inset-0" />
      <div className="pointer-events-none absolute -left-40 top-0 h-[480px] w-[480px] rounded-full bg-electric/20 blur-[140px]" />
      <div className="pointer-events-none absolute -right-32 bottom-0 h-[380px] w-[380px] rounded-full bg-electric2/10 blur-[120px]" />

      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <motion.p {...fade} transition={{ duration: 0.5 }} className="tech-label text-electric2">
          The Problem
        </motion.p>
        <motion.h2
          {...fade}
          transition={{ duration: 0.6, delay: 0.08 }}
          className="mt-4 max-w-2xl font-display text-4xl leading-tight tracking-tight md:text-5xl"
        >
          A Small Crop With a <span className="text-gradient-blue">Big Impact</span>.
        </motion.h2>
        <motion.p
          {...fade}
          transition={{ duration: 0.6, delay: 0.16 }}
          className="mt-6 max-w-2xl leading-relaxed text-slate-400"
        >
          Onions are one of the most widely grown crops in the world — yet in many fields,
          monitoring them is still done by eye, from memory, and too late. Growers and
          students experimenting with smart farming face the same wall: the crop is in the
          ground, the signs are visible, but there is no simple system to observe and
          record them consistently.
        </motion.p>

        {/* topic cards — staggered, asymmetric grid */}
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["Crop Monitoring", "Watching an onion crop through its full growth cycle is hard to do consistently by hand — the field is large, the changes are gradual."],
            ["Health Observation", "Visible stress often appears on the plant before it becomes a lost harvest. Catching it early depends on regular, disciplined observation."],
            ["Disease Identification", "Many onion diseases show up as patterns on the leaves and bulb skin. Identifying them correctly needs reference, experience and attention."],
            ["Soil & Environment", "Moisture and field conditions drive how the crop develops. Without sensors or records, watering decisions rely mostly on guesswork."],
            ["Early Detection", "The earlier a problem is noticed, the cheaper it is to manage. Late detection usually means loss — a challenge for every small farm."],
            ["Better Decisions", "When observations are captured and organised, farmers, students and researchers can make choices based on evidence instead of instinct."],
          ].map(([title, body], i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 26 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.55, delay: i * 0.08 }}
              className={`glass-dark group rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1.5 hover:border-electric/40 ${
                i % 3 === 1 ? "lg:translate-y-6" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="tech-label text-electric2">0{i + 1}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-electric pulse-dot opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              </div>
              <h3 className="mt-4 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
            </motion.div>
          ))}
        </div>

        <motion.p
          {...fade}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-12 max-w-2xl border-l-2 border-electric/50 pl-5 text-sm leading-relaxed text-slate-500"
        >
          ONION LAB is a student-built exploration of this problem: what can a camera,
          a browser and open tooling honestly observe about an onion crop — and where
          does measurement have to stop?
        </motion.p>
      </div>
    </section>
  );
}
