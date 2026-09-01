import React from "react";
import { motion, useReducedMotion } from "framer-motion";

/** Small floating technical UI chip that gently drifts around the 3D onion. */
export default function FloatingSensorCard({ label, value, accent = false, delay = 0, className = "" }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: reduce ? 0 : [0, -8, 0] }}
      transition={{
        opacity: { duration: 0.7, delay },
        y: reduce ? { duration: 0.7, delay } : { duration: 5.5, repeat: Infinity, ease: "easeInOut", delay },
      }}
      className={`glass rounded-xl px-3.5 py-2.5 shadow-soft ${className}`}
    >
      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${accent ? "bg-electric pulse-dot" : "bg-emerald-500 pulse-dot"}`} />
        <span className="tech-label text-mutext">{label}</span>
      </div>
      <div className="mt-1 font-mono text-sm font-medium text-fg">{value}</div>
    </motion.div>
  );
}
