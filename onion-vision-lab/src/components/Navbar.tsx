import { useEffect, useState } from 'react';
import { requestCameraStart } from '../services/cameraBus';

const LINKS: Array<[string, string]> = [
  ['Home', '#home'],
  ['Project', '#project'],
  ['How it works', '#how'],
  ['Vision Lab', '#vision-lab'],
  ['3D Explorer', '#explorer'],
  ['Metrics', '#metrics'],
];

interface NavbarProps {
  demoEngine: boolean;
  health: { ok: boolean; text: string } | null;
}

export default function Navbar({ demoEngine, health }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const launchCamera = () => {
    document.getElementById('vision-lab')?.scrollIntoView({ behavior: 'smooth' });
    setTimeout(() => requestCameraStart(), 650);
    setOpen(false);
  };

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? 'glass-strong shadow-soft' : 'bg-transparent'
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 md:px-8">
        <a href="#home" className="flex items-center gap-2.5">
          <span className="relative grid h-9 w-9 place-items-center">
            <span className="absolute inset-0 rounded-full border border-electric/40 ring-spin" />
            <span className="absolute inset-0.5 rounded-full border border-dashed border-electric2/40 ring-spin-rev" />
            <span className="grid h-6 w-6 place-items-center rounded-full bg-gradient-to-br from-electric to-electric2 text-[11px] font-bold text-white shadow-glow">
              O
            </span>
          </span>
          <span className="font-mono text-[13px] font-bold tracking-[0.18em] text-fg">
            ONION VISION LAB
          </span>
        </a>

        <div className="hidden items-center gap-6 lg:flex">
          {LINKS.map(([label, href]) => (
            <a
              key={href}
              href={href}
              className="text-[13px] font-medium text-mutext transition-colors hover:text-electric"
            >
              {label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2.5">
          <span
            className={`tech-label hidden rounded-full border px-2.5 py-1 sm:block ${
              demoEngine
                ? 'border-amber-300 bg-amberSoft text-amber'
                : 'border-green-300 bg-greenSoft text-green'
            }`}
          >
            {demoEngine ? 'DEMO ENGINE' : 'LIVE'}
          </span>
          <span className="mono hidden rounded-full border border-line bg-white/80 px-2.5 py-1 text-[10px] text-mutext xl:block">
            {health ? (health.ok ? `API ✓ ${health.text}` : 'API unreachable → demo fallback') : 'API …'}
          </span>
          <button onClick={launchCamera} className="btn-primary-blue hidden h-10 px-5 text-sm md:flex">
            Launch Camera
          </button>
          <button
            onClick={() => setOpen((v) => !v)}
            aria-label="Menu"
            className="grid h-10 w-10 place-items-center rounded-lg border border-line bg-white/80 lg:hidden"
          >
            <div className="space-y-1.5">
              <span className={`block h-0.5 w-5 bg-fg transition ${open ? 'translate-y-2 rotate-45' : ''}`} />
              <span className={`block h-0.5 w-5 bg-fg transition ${open ? 'opacity-0' : ''}`} />
              <span className={`block h-0.5 w-5 bg-fg transition ${open ? '-translate-y-2 -rotate-45' : ''}`} />
            </div>
          </button>
        </div>
      </nav>

      {open && (
        <div className="glass-strong border-t border-line px-5 py-4 lg:hidden">
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
          <button onClick={launchCamera} className="btn-primary-blue mt-3 h-11 w-full text-sm">
            Launch Camera
          </button>
        </div>
      )}
    </header>
  );
}
