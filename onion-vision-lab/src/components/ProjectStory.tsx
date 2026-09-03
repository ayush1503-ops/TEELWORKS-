import { motion } from 'framer-motion';

const fade = {
  initial: { opacity: 0, y: 28 },
  whileInView: { opacity: 1, y: 0 } as const,
  viewport: { once: true, margin: '-70px' } as const,
};

const TOPICS: Array<[string, string]> = [
  [
    'Surface Discoloration',
    'Darker or uneven colour patches on the skin. A camera can genuinely measure these from pixels — colour ratios, not opinions.',
  ],
  [
    'Surface Damage',
    'Cuts, marks or broken-looking skin visible from the photographed side. Visible damage is a real, camera-observable signal.',
  ],
  [
    'Possible Mold-Like Growth',
    'Grey/green fuzzy-looking spots that could be mould. The system says "possible" — it never certifies food safety.',
  ],
  [
    'Shriveling',
    'Dry, wrinkled-looking skin reads as higher micro-texture and low saturation spread — a measurable surface cue.',
  ],
  [
    'Sprouting',
    'A green shoot starting to grow. Green-coloured pixels near the top of the bulb are a clear, visible early signal.',
  ],
  [
    'The honest limit',
    'Black mold inside or hollow heart stay invisible to every camera. The app says so on every screen — internal quality is never claimed.',
  ],
];

export default function ProjectStory() {
  return (
    <section id="project" className="relative scroll-mt-20 overflow-hidden bg-[#F7F9FF] py-24 md:py-28">
      <div className="dot-grid-soft pointer-events-none absolute inset-0" />
      <div className="pointer-events-none absolute -left-40 top-0 h-[420px] w-[420px] rounded-full bg-electric/10 blur-[130px]" />

      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <motion.p {...fade} transition={{ duration: 0.5 }} className="tech-label text-electric">
          The problem
        </motion.p>
        <motion.h2
          {...fade}
          transition={{ duration: 0.6, delay: 0.08 }}
          className="mt-4 max-w-3xl font-display text-4xl font-extrabold leading-tight tracking-tight text-fg md:text-5xl"
        >
          In a mandi, quality is decided by eye —{' '}
          <span className="text-gradient-blue">often too late</span>.
        </motion.h2>
        <motion.p
          {...fade}
          transition={{ duration: 0.6, delay: 0.16 }}
          className="mt-6 max-w-2xl leading-relaxed text-mutext"
        >
          Onions are graded in seconds: by feel, by colour, by a quick glance at
          the skin. Post-harvest losses are huge, and most small buyers and
          mandi workers do not have a lab. A phone camera is something everyone
          has — but a camera can only ever judge what it can see. Onion Vision
          Lab is built on exactly that boundary: it measures the visible surface
          honestly, and it says out loud what no camera can know.
        </motion.p>

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {TOPICS.map(([title, body], i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-50px' }}
              transition={{ duration: 0.55, delay: i * 0.07 }}
              className={`glass group rounded-2xl p-6 shadow-soft transition-all duration-300 hover:-translate-y-1.5 hover:shadow-lift ${
                i === 5 ? 'ring-1 ring-amber-300/70' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="tech-label text-electric2">0{i + 1}</span>
                {i === 5 ? (
                  <span className="tech-label rounded-full bg-amberSoft px-2.5 py-1 text-amber">not visible</span>
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-electric pulse-dot opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                )}
              </div>
              <h3 className="mt-4 text-lg font-bold text-fg">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mutext">{body}</p>
            </motion.div>
          ))}
        </div>

        <motion.p
          {...fade}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mt-12 max-w-3xl border-l-2 border-electric/50 pl-5 text-sm leading-relaxed text-mutext"
        >
          Only five findings are ever reported — Surface Discoloration, Surface
          Damage, Possible Mold-Like Growth, Shriveling, Sprouting — each with a
          plain-language explanation. Nothing else is invented.
        </motion.p>
      </div>
    </section>
  );
}
