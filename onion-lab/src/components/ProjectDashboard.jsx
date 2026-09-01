import React from "react";
import { motion } from "framer-motion";

/* All values below are SAMPLE demonstration data — clearly labelled. */

const METRICS = [
  { label: "Soil Moisture", value: "68%", bar: 68, unit: "SAMPLE" },
  { label: "Growth Stage", value: "VEGETATIVE", bar: 46, unit: "SAMPLE" },
  { label: "Camera Status", value: "READY", bar: 100, unit: "LIVE UI" },
  { label: "Project Status", value: "ACTIVE", bar: 92, unit: "TRUE" },
];

export default function ProjectDashboard() {
  return (
    <section id="dashboard" className="relative scroll-mt-20 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="tech-label text-electric"
            >
              Project Dashboard
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.08 }}
              className="mt-3 font-display text-4xl tracking-tight md:text-5xl"
            >
              The Project at a <span className="text-gradient-blue">Glance</span>
            </motion.h2>
          </div>
          <motion.span
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="tech-label self-start rounded-full border border-amber-300/60 bg-amber-50 px-3.5 py-1.5 text-amber-600 md:self-auto"
          >
            ⚠ Demonstration data — not live sensors
          </motion.span>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {METRICS.map((m, i) => (
            <motion.div
              key={m.label}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              whileHover={{ y: -6 }}
              className="rounded-2xl border border-slate-100 bg-white p-6 shadow-soft transition-shadow hover:shadow-lift"
            >
              <div className="flex items-center justify-between">
                <span className="tech-label text-mutext">{m.label}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-electric pulse-dot" />
              </div>
              <div className="mt-4 font-mono text-2xl font-bold tracking-tight text-fg">
                {m.value}
              </div>
              <div className="mt-5 h-1 w-full overflow-hidden rounded-full bg-muted">
                <motion.div
                  initial={{ width: 0 }}
                  whileInView={{ width: `${m.bar}%` }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.3 + i * 0.12, ease: "easeOut" }}
                  className="h-full rounded-full bg-gradient-to-r from-electric to-electric2"
                />
              </div>
              <p className="mt-3 font-mono text-[10px] tracking-[0.18em] text-mutext/70">
                {m.unit}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
