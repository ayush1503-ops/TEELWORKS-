import React, { useEffect, useState } from "react";
import { requestCameraStart } from "../lib/cameraBus";

const LINKS = [
  ["Home", "#home"],
  ["Project", "#project"],
  ["Vision Lab", "#vision-lab"],
  ["3D Explorer", "#explorer"],
  ["About", "#about"],
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const launchCamera = () => {
    document.getElementById("vision-lab")?.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => requestCameraStart(), 650);
    setOpen(false);
  };

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? "glass shadow-soft" : "bg-transparent"
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 md:px-8">
        <a href="#home" className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-electric to-electric2 text-sm font-bold text-white shadow-glow">
            O
          </span>
          <span className="font-mono text-sm font-bold tracking-[0.22em] text-fg">
            ONION&nbsp;LAB
          </span>
        </a>

        <div className="hidden items-center gap-7 md:flex">
          {LINKS.map(([label, href]) => (
            <a
              key={href}
              href={href}
              className="text-sm font-medium text-mutext transition-colors hover:text-electric"
            >
              {label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={launchCamera}
            className="btn-primary-blue hidden h-10 items-center rounded-lg px-5 text-sm font-semibold md:flex"
          >
            Launch Camera
          </button>
          {/* mobile menu */}
          <button
            onClick={() => setOpen((v) => !v)}
            aria-label="Menu"
            className="grid h-10 w-10 place-items-center rounded-lg border border-slate-200 bg-white/70 md:hidden"
          >
            <div className="space-y-1.5">
              <span className="block h-0.5 w-5 bg-fg" />
              <span className="block h-0.5 w-5 bg-fg" />
            </div>
          </button>
        </div>
      </nav>

      {open && (
        <div className="glass border-t border-slate-100 px-5 py-4 md:hidden">
          {LINKS.map(([label, href]) => (
            <a
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              className="block py-2.5 text-sm font-medium text-fg"
            >
              {label}
            </a>
          ))}
          <button onClick={launchCamera} className="btn-primary-blue mt-3 h-11 w-full rounded-lg text-sm font-semibold">
            Launch Camera
          </button>
        </div>
      )}
    </header>
  );
}
