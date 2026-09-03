import { motion } from 'framer-motion';

const STEPS: Array<[string, string, string]> = [
  [
    '01',
    'Point',
    'Aim the camera at one onion or a whole pile. No login, no training, no manual — anyone can do this.',
  ],
  [
    '02',
    'See colours',
    'While you are only pointing, an on-device colour heuristic draws boxes live and says fresh / suspect / strong dark colours. That is the colour preview — not the AI model.',
  ],
  [
    '03',
    'Tap once',
    'Capture the photo. YOLO finds every onion, the TensorFlow verifier gates look-alikes, and the PyTorch CNN + RandomForest + HSV signals are fused per onion.',
  ],
  [
    '04',
    'Read & share',
    'GREEN / YELLOW / RED verdicts in plain language, a formal PDF report, and an optional deep 3D analysis — always labelled with what was and was not measured.',
  ],
];

export default function HowItWorks() {
  return (
    <section id="how" className="relative scroll-mt-20 overflow-hidden py-24 md:py-28">
      <div className="dot-grid pointer-events-none absolute inset-0 opacity-40" />
      <div className="relative mx-auto max-w-7xl px-5 md:px-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="tech-label text-electric"
            >
              How it works
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.08 }}
              className="mt-3 font-display text-4xl font-extrabold tracking-tight text-fg md:text-5xl"
            >
              Zero training. <span className="text-gradient-blue">One tap.</span>
            </motion.h2>
          </div>
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="max-w-sm text-sm leading-relaxed text-mutext"
          >
            Advanced inside — multi-framework AI with measured, honest numbers.
            Simple outside — one primary flow with big buttons.
          </motion.p>
        </div>

        <div className="relative mt-16">
          <motion.div
            initial={{ scaleX: 0, scaleY: 0 }}
            whileInView={{ scaleX: 1, scaleY: 1 }}
            viewport={{ once: true, margin: '-70px' }}
            transition={{ duration: 1, ease: 'easeOut' }}
            className="absolute left-[27px] top-0 h-full w-px origin-top bg-gradient-to-b from-electric/60 via-electric/20 to-transparent md:left-0 md:right-0 md:top-[27px] md:h-px md:w-full md:origin-left md:bg-gradient-to-r"
          />
          <div className="grid gap-10 md:grid-cols-4 md:gap-6">
            {STEPS.map(([num, title, body], i) => (
              <motion.div
                key={num}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.55, delay: 0.15 + i * 0.16 }}
                className="relative flex gap-5 md:block"
              >
                <div className="relative z-10 grid h-14 w-14 shrink-0 place-items-center rounded-full border border-electric/30 bg-white font-mono text-sm font-bold text-electric shadow-glow">
                  <span className="absolute inset-0 rounded-full bg-electric/10 blur-md" />
                  <span className="relative">{num}</span>
                </div>
                <div className="md:mt-6">
                  <h3 className="font-mono text-sm font-bold uppercase tracking-[0.14em] text-fg">{title}</h3>
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
