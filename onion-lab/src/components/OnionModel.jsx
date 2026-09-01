import React, { useMemo, useRef, useEffect, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, Float } from "@react-three/drei";
import * as THREE from "three";
import { useReducedMotion } from "framer-motion";

/* ------------------------------------------------------------------ *
 * Procedural 3D onion (no external .glb needed):
 *   sphere displaced with vertical ribs + basal swell + top taper
 *   layered papery skin shells, neck, root tuft
 *   canvas-generated skin texture (works fully offline)
 * Interaction: drag rotate (pointer), wheel zoom, pinch zoom, RESET
 * ------------------------------------------------------------------ */

function makeSkinTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const ctx = c.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0, "#b4653a");
  grad.addColorStop(0.45, "#9c4a24");
  grad.addColorStop(1, "#7e3517");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 512);
  // vertical papery streaks
  for (let i = 0; i < 160; i++) {
    const x = Math.random() * 512;
    const w = 1 + Math.random() * 4;
    const a = 0.04 + Math.random() * 0.1;
    ctx.fillStyle =
      Math.random() > 0.5 ? `rgba(230,190,150,${a})` : `rgba(60,25,10,${a})`;
    ctx.fillRect(x, Math.random() * 60, w, 512);
  }
  // speckle
  for (let i = 0; i < 900; i++) {
    ctx.fillStyle = `rgba(40,18,8,${0.03 + Math.random() * 0.08})`;
    ctx.fillRect(Math.random() * 512, Math.random() * 512, 1.6, 1.6);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

function makeBumpTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#808080";
  ctx.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 200; i++) {
    const x = Math.random() * 512;
    const w = 2 + Math.random() * 6;
    const g = 100 + Math.floor(Math.random() * 110);
    ctx.fillStyle = `rgba(${g},${g},${g},0.35)`;
    ctx.fillRect(x, 0, w, 512);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

function useOnionGeometry() {
  return useMemo(() => {
    const geo = new THREE.SphereGeometry(1, 128, 128);
    const pos = geo.attributes.position;
    const v = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);
      const theta = Math.atan2(v.z, v.x);
      const phi = Math.acos(THREE.MathUtils.clamp(v.y, -1, 1));
      let r = 1;
      r *= 1 + 0.05 * Math.cos(7 * theta) * Math.sin(phi);   // vertical ribs
      r *= 1 - 0.16 * Math.pow(Math.max(0, v.y), 2.2);       // taper to the neck
      r *= 1 + 0.07 * Math.pow(Math.max(0, -v.y), 2);        // basal plate swell
      v.multiplyScalar(r);
      pos.setXYZ(i, v.x, v.y * 0.94, v.z);
    }
    geo.computeVertexNormals();
    return geo;
  }, []);
}

function OnionMesh({ skinMap, bumpMap }) {
  const geo = useOnionGeometry();
  const skin = useMemo(
    () => ({
      bulb: new THREE.MeshStandardMaterial({
        map: skinMap, bumpMap, bumpScale: 0.035,
        roughness: 0.62, metalness: 0.05,
      }),
      shellOuter: new THREE.MeshStandardMaterial({
        map: skinMap, transparent: true, opacity: 0.16,
        roughness: 0.95, depthWrite: false,
      }),
    }),
    [skinMap, bumpMap]
  );
  return (
    <group>
      <mesh geometry={geo} material={skin.bulb} castShadow />
      <mesh geometry={geo} material={skin.shellOuter} scale={1.045} />
      {/* neck */}
      <mesh position={[0, 0.86, 0]} rotation={[0.06, 0, 0.05]}>
        <coneGeometry args={[0.16, 0.5, 24]} />
        <meshStandardMaterial color="#c8a06a" roughness={0.9} />
      </mesh>
      {/* dried leaf tips */}
      {[-0.09, 0.02, 0.1].map((x, i) => (
        <mesh key={i} position={[x, 1.12, i * 0.04 - 0.04]} rotation={[0.1 * i, 0, x * 2.2]}>
          <coneGeometry args={[0.045, 0.42, 10]} />
          <meshStandardMaterial color="#cdb289" roughness={1} />
        </mesh>
      ))}
      {/* root tuft */}
      {[-0.1, -0.03, 0.04, 0.11].map((x, i) => (
        <mesh key={i} position={[x, -0.98, (i % 2) * 0.06 - 0.03]} rotation={[0.16 * i, 0, x * 1.4]}>
          <cylinderGeometry args={[0.012, 0.004, 0.34, 6]} />
          <meshStandardMaterial color="#b9a179" roughness={1} />
        </mesh>
      ))}
    </group>
  );
}

function Rig({ autoRotate, reduceMotion, api }) {
  // api: { targets, zoomRef, dragging }
  const group = useRef();
  const { camera, pointer } = useThree();
  useFrame((_, delta) => {
    const g = group.current;
    if (!g) return;
    const t = api.targets;
    if (autoRotate && !api.dragging.current && !reduceMotion) t.rotY += delta * 0.22;
    g.rotation.y = THREE.MathUtils.damp(g.rotation.y, t.rotY, 5, delta);
    g.rotation.x = THREE.MathUtils.damp(g.rotation.x, t.rotX, 5, delta);
    // gentle mouse parallax
    if (!reduceMotion && !api.dragging.current) {
      g.rotation.z = THREE.MathUtils.damp(g.rotation.z, pointer.x * 0.04, 4, delta);
      g.position.y = THREE.MathUtils.damp(g.position.y, pointer.y * 0.05, 4, delta);
    }
    const z = THREE.MathUtils.damp(camera.position.z, api.zoomRef.current, 5, delta);
    camera.position.z = z;
  });
  return (
    <group ref={group}>
      <Float speed={reduceMotion ? 0 : 1.4} rotationIntensity={0.15} floatIntensity={reduceMotion ? 0 : 0.35}>
        <OnionMeshGlobal api={api} />
      </Float>
    </group>
  );
}

// separate so textures are created once via useMemo in a child
let _skinCache = null;
let _bumpCache = null;
function OnionMeshGlobal({ api }) {
  if (!_skinCache) _skinCache = makeSkinTexture();
  if (!_bumpCache) _bumpCache = makeBumpTexture();
  return <OnionMesh skinMap={_skinCache} bumpMap={_bumpCache} />;
}

export default function OnionModel({
  height = 560,
  autoRotate = true,
  controls = true,
  className = "",
}) {
  const wrapRef = useRef(null);
  const reduceMotion = useReducedMotion();
  const targets = useRef({ rotX: 0.12, rotY: 0.4 }).current;
  const zoomRef = useRef(4.6);
  const dragging = useRef(false);
  const pointers = useRef(new Map());
  const lastPinch = useRef(0);
  const api = useMemo(() => ({ targets, zoomRef, dragging }), []);

  const onPointerDown = useCallback((e) => {
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    dragging.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
  }, []);

  const onPointerMove = useCallback((e) => {
    const p = pointers.current.get(e.pointerId);
    if (!p) return;
    const dx = e.clientX - p.x;
    const dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    if (pointers.current.size === 1) {
      targets.rotY += dx * 0.006;
      targets.rotX = THREE.MathUtils.clamp(targets.rotX + dy * 0.004, -0.6, 0.9);
    } else if (pointers.current.size === 2) {
      const pts = [...pointers.current.values()];
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      if (lastPinch.current) {
        zoomRef.current = THREE.MathUtils.clamp(
          zoomRef.current - (dist - lastPinch.current) * 0.01, 2.8, 7.5
        );
      }
      lastPinch.current = dist;
    }
  }, [targets, zoomRef]);

  const endPointer = useCallback((e) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) lastPinch.current = 0;
    if (pointers.current.size === 0) dragging.current = false;
  }, []);

  // wheel zoom (non-passive so we can preventDefault)
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      zoomRef.current = THREE.MathUtils.clamp(zoomRef.current + e.deltaY * 0.002, 2.8, 7.5);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoomRef]);

  const [rotating, setRotating] = React.useState(true);
  const [zoomed, setZoomed] = React.useState(false);

  return (
    <div className={"relative " + className} style={{ height }}>
      <div
        ref={wrapRef}
        className="absolute inset-0 cursor-grab active:cursor-grabbing touch-none"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endPointer}
        onPointerCancel={endPointer}
      >
        <Canvas shadows camera={{ position: [0, 0.4, 4.6], fov: 42 }} dpr={[1, 2]}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[4, 6, 4]} intensity={1.5} color="#fff4e8" castShadow />
          {/* electric-blue atmospheric rim lights */}
          <pointLight position={[-5, 2, -4]} intensity={26} color="#0052ff" distance={14} />
          <pointLight position={[4, -2, -3]} intensity={12} color="#4d7cff" distance={12} />
          <Rig autoRotate={rotating && autoRotate} reduceMotion={reduceMotion} api={api} />
          <ContactShadows position={[0, -1.35, 0]} opacity={0.35} scale={6} blur={2.6} far={3} color="#1e293b" />
        </Canvas>
      </div>

      {controls && (
        <div className="absolute bottom-3 left-1/2 z-10 flex -translate-x-1/2 gap-2">
          {[
            { k: "rotate", label: "ROTATE", on: rotating, act: () => setRotating((v) => !v) },
            { k: "zoom", label: "ZOOM", on: zoomed, act: () => { const nz = !zoomed; setZoomed(nz); zoomRef.current = nz ? 3.1 : 4.6; } },
            { k: "reset", label: "RESET", on: false, act: () => { targets.rotX = 0.12; targets.rotY = 0.4; zoomRef.current = 4.6; setZoomed(false); setRotating(true); } },
          ].map((b) => (
            <button
              key={b.k}
              onClick={b.act}
              className={`tech-label rounded-full border px-4 py-2 transition-all ${
                b.on
                  ? "border-electric/60 bg-electric/10 text-electric shadow-glow"
                  : "border-slate-200 bg-white/80 text-mutext hover:border-electric/40 hover:text-electric"
              }`}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
