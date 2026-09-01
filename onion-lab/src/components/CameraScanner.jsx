import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cameraBus } from "../lib/cameraBus";

/* ------------------------------------------------------------------ *
 * CameraScanner — browser-native camera with a computer-vision style
 * scanning overlay. HONESTY: no real detection model is connected in
 * this frontend demo, so the overlay is clearly labelled DEMO ANALYSIS.
 * Privacy: the stream never leaves the browser (no upload, no storage).
 * ------------------------------------------------------------------ */

const STATUS = {
  IDLE: "idle",
  REQUESTING: "requesting",
  ACTIVE: "active",
  DENIED: "denied",
  UNSUPPORTED: "unsupported",
};

export default function CameraScanner({ compact = false }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const rafRef = useRef(0);
  const frames = useRef(0);
  const lastFpsT = useRef(performance.now());
  const [status, setStatus] = useState(STATUS.IDLE);
  const [fps, setFps] = useState(0);
  const [errMsg, setErrMsg] = useState("");
  const reduce = useReducedMotion();

  const stopCamera = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop()); // release camera
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    setStatus(STATUS.IDLE);
    setFps(0);
  }, []);

  // cleanup on unmount — never leave a live camera behind
  useEffect(() => stopCamera, [stopCamera]);

  const startCamera = useCallback(async () => {
    setErrMsg("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus(STATUS.UNSUPPORTED);
      return;
    }
    setStatus(STATUS.REQUESTING);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setStatus(STATUS.ACTIVE);
      // FPS counter
      const tick = () => {
        frames.current++;
        const now = performance.now();
        if (now - lastFpsT.current >= 1000) {
          setFps(Math.round((frames.current * 1000) / (now - lastFpsT.current)));
          frames.current = 0;
          lastFpsT.current = now;
        }
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    } catch (err) {
      if (err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError") {
        setStatus(STATUS.DENIED);
        setErrMsg(
          "Camera permission was denied. Allow camera access in your browser settings (padlock icon in the address bar), then try again."
        );
      } else if (err?.name === "NotFoundError" || err?.name === "OverconstrainedError") {
        setStatus(STATUS.DENIED);
        setErrMsg("No camera device was found on this system.");
      } else {
        setStatus(STATUS.DENIED);
        setErrMsg(err?.message || "The camera could not be started.");
      }
    }
  }, []);

  // external "Start Camera" buttons (hero / navbar) activate this scanner
  useEffect(() => {
    const h = () => {
      if (status === STATUS.IDLE || status === STATUS.DENIED || status === STATUS.UNSUPPORTED) {
        startCamera();
      }
    };
    cameraBus.addEventListener("start", h);
    return () => cameraBus.removeEventListener("start", h);
  }, [status, startCamera]);

  const active = status === STATUS.ACTIVE;

  return (
    <div className={`relative w-full ${compact ? "" : "mx-auto max-w-3xl"}`}>
      {/* ---------- viewport frame ---------- */}
      <div className="scanlines relative aspect-[4/3] w-full overflow-hidden rounded-2xl border border-slate-800 bg-dark shadow-lift">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`h-full w-full object-cover ${active ? "opacity-100" : "opacity-0"}`}
        />

        {/* idle / requesting / error states */}
        <AnimatePresence>
          {!active && (
            <motion.div
              key="cover"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-dark px-6 text-center"
            >
              <div className="dot-grid-light absolute inset-0" />
              {status === STATUS.REQUESTING ? (
                <>
                  <div className="h-10 w-10 animate-spin rounded-full border-2 border-electric2 border-t-transparent" />
                  <p className="tech-label text-electric2">Requesting camera permission…</p>
                </>
              ) : status === STATUS.DENIED || status === STATUS.UNSUPPORTED ? (
                <>
                  <p className="tech-label text-red-400">
                    {status === STATUS.UNSUPPORTED ? "Camera unsupported" : "Camera unavailable"}
                  </p>
                  <p className="max-w-sm text-sm leading-relaxed text-slate-400">{errMsg}</p>
                  <button
                    onClick={startCamera}
                    className="btn-primary-blue mt-1 h-11 rounded-lg px-6 text-sm font-semibold"
                  >
                    Try again
                  </button>
                </>
              ) : (
                <>
                  <div className="grid h-14 w-14 place-items-center rounded-2xl border border-electric/40 bg-electric/10 text-2xl">
                    ◉
                  </div>
                  <p className="tech-label text-slate-400">Camera standby</p>
                  <p className="max-w-xs text-xs leading-relaxed text-slate-500">
                    Click Start Camera to grant access. Video is processed locally in your
                    browser — nothing is uploaded or stored.
                  </p>
                  <button
                    onClick={startCamera}
                    className="btn-primary-blue mt-1 h-11 rounded-lg px-6 text-sm font-semibold"
                  >
                    Start Camera
                  </button>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ---------- scanning overlay ---------- */}
        {active && (
          <>
            {/* corner brackets */}
            {[
              "left-4 top-4 border-l-2 border-t-2",
              "right-4 top-4 border-r-2 border-t-2",
              "bottom-4 left-4 border-b-2 border-l-2",
              "bottom-4 right-4 border-b-2 border-r-2",
            ].map((pos) => (
              <div key={pos} className={`pointer-events-none absolute h-9 w-9 rounded-sm border-electric2/90 ${pos}`} />
            ))}

            {/* scanning frame */}
            <div className="pointer-events-none absolute inset-9 rounded-xl border border-electric2/30" />

            {/* animated scanning line */}
            {!reduce && (
              <motion.div
                className="pointer-events-none absolute left-9 right-9 h-16"
                style={{
                  background:
                    "linear-gradient(180deg, rgba(0,82,255,0) 0%, rgba(0,82,255,0.28) 50%, rgba(0,82,255,0) 100%)",
                }}
                animate={{ top: ["12%", "78%", "12%"] }}
                transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
              />
            )}

            {/* technical labels */}
            <div className="pointer-events-none absolute left-5 top-5 space-y-1.5">
              <div className="flex items-center gap-2 rounded-md bg-black/45 px-2.5 py-1 backdrop-blur-sm">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500 pulse-dot" />
                <span className="tech-label text-white">● Camera Active</span>
              </div>
              <div className="rounded-md bg-black/45 px-2.5 py-1 backdrop-blur-sm">
                <span className="tech-label text-electric2">Vision System</span>
              </div>
            </div>
            <div className="pointer-events-none absolute right-5 top-5 space-y-1.5 text-right">
              <div className="rounded-md bg-black/45 px-2.5 py-1 backdrop-blur-sm">
                <span className="tech-label text-amber-300">Demo Analysis · Simulation</span>
              </div>
              <div className="rounded-md bg-black/45 px-2.5 py-1 backdrop-blur-sm">
                <span className="tech-label text-slate-300">{fps} FPS</span>
              </div>
            </div>
            <div className="pointer-events-none absolute bottom-5 left-5 right-5 flex items-end justify-between">
              <div className="rounded-md bg-black/45 px-2.5 py-1 backdrop-blur-sm">
                <span className="tech-label text-slate-300">Object Detection: not connected</span>
              </div>
              <motion.div
                animate={reduce ? {} : { opacity: [1, 0.35, 1] }}
                transition={{ duration: 1.6, repeat: Infinity }}
                className="rounded-md bg-electric/25 px-2.5 py-1 backdrop-blur-sm"
              >
                <span className="tech-label text-white">Analyzing…</span>
              </motion.div>
            </div>
          </>
        )}
      </div>

      {/* ---------- controls under the frame ---------- */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${active ? "bg-emerald-400 pulse-dot" : "bg-slate-300"}`} />
          <span className="tech-label text-mutext">
            {active ? "STREAM: LIVE · LOCAL ONLY" : "STREAM: OFF"}
          </span>
        </div>
        {active ? (
          <button
            onClick={stopCamera}
            className="h-11 rounded-lg border border-red-200 bg-red-50 px-6 text-sm font-semibold text-red-600 transition-all hover:bg-red-100"
          >
            ■ Stop Camera
          </button>
        ) : (
          status !== STATUS.REQUESTING && (
            <button
              onClick={startCamera}
              className="h-11 rounded-lg border border-slate-200 bg-white px-6 text-sm font-semibold text-fg transition-all hover:border-electric/40 hover:text-electric"
            >
              ▶ Start Camera
            </button>
          )
        )}
      </div>
    </div>
  );
}
