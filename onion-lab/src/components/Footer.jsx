import React from "react";

export default function Footer() {
  return (
    <footer id="about" className="scroll-mt-20 border-t border-slate-100 bg-white">
      <div className="mx-auto max-w-7xl px-5 py-16 md:px-8">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-electric to-electric2 text-sm font-bold text-white">
                O
              </span>
              <span className="font-mono text-sm font-bold tracking-[0.22em]">ONION LAB</span>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-mutext">
              A student-built smart farming project exploring how computer vision
              and interactive 3D can make onion crop monitoring more objective,
              observable and open.
            </p>
          </div>
          <div>
            <p className="tech-label text-mutext">System</p>
            <ul className="mt-4 space-y-2.5 text-sm text-fg/80">
              <li>Camera — local browser only</li>
              <li>3D — procedural WebGL onion</li>
              <li>Analysis overlay — DEMO / simulation</li>
              <li>No footage uploaded or stored</li>
            </ul>
          </div>
          <div>
            <p className="tech-label text-mutext">Honesty Notes</p>
            <ul className="mt-4 space-y-2.5 text-sm text-fg/80">
              <li>Detection labels are simulated until a model is connected</li>
              <li>Dashboard values are sample data</li>
              <li>Companion grading app: Onion Quality Analyzer (SIH 26031)</li>
            </ul>
          </div>
        </div>
        <div className="mt-14 flex flex-col items-start justify-between gap-3 border-t border-slate-100 pt-6 md:flex-row md:items-center">
          <p className="font-mono text-xs text-mutext">© {new Date().getFullYear()} ONION LAB — university innovation project</p>
          <p className="font-mono text-xs text-mutext/70">Built with React · Three.js · Framer Motion</p>
        </div>
      </div>
    </footer>
  );
}
