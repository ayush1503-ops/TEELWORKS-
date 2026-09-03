export default function Footer() {
  return (
    <footer id="about" className="scroll-mt-20 border-t border-line bg-white">
      <div className="mx-auto max-w-7xl px-5 py-14 md:px-8">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1.2fr]">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-electric to-electric2 text-sm font-bold text-white shadow-glow">
                O
              </span>
              <span className="font-mono text-sm font-bold tracking-[0.18em] text-fg">ONION VISION LAB</span>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-mutext">
              A student-built Smart Onion Project (SIH PS 26031): camera-based,
              visible-surface quality inspection for mandi workers, shopkeepers
              and consumers. Advanced multi-framework AI inside; one-tap
              simplicity outside; honest scope everywhere.
            </p>
          </div>
          <div>
            <p className="tech-label text-mutext">System</p>
            <ul className="mt-4 space-y-2.5 text-sm text-fg/80">
              <li>• Detector — YOLOv8n single-class (ONNX)</li>
              <li>• Verifier — TensorFlow gate (ONNX)</li>
              <li>• Condition — PyTorch CNN + RF + HSV fusion</li>
              <li>• Live colour preview — on-device, in-memory</li>
              <li>• Camera permission only on click; frames never stored</li>
            </ul>
          </div>
          <div>
            <p className="tech-label text-mutext">Honesty notes</p>
            <ul className="mt-4 space-y-2.5 text-sm leading-relaxed text-fg/80">
              <li>• Analysis is limited to the visible surface photographed.</li>
              <li>• Internal quality cannot be determined by any camera — no claim is made about the inside of an onion.</li>
              <li>• Confidence values are visual prediction confidences, never food-safety probabilities.</li>
              <li>• Variety labels are colour estimates; numbers always carry their scope.</li>
            </ul>
          </div>
        </div>
        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-line pt-6 md:flex-row md:items-center">
          <p className="mono text-xs text-mutext">
            © {new Date().getFullYear()} Onion Vision Lab — Smart Onion Project (SIH PS 26031)
          </p>
          <p className="mono text-xs text-mutext/80">React · Three.js · Framer Motion · FastAPI · ONNX Runtime · OpenCV</p>
        </div>
      </div>
    </footer>
  );
}
