/**
 * OnionModel — procedural 3D onion (no .glb needed) with:
 *   ribs + top taper + basal swell + papery shell + neck + roots
 * and OPTIONAL photo texturing: the photographed side of a real onion crop
 * can be texture-mapped onto the bulb. Only the photographed side is real
 * evidence — the far side repeats the photographed texture (honesty caption
 * must be shown by callers).
 * Optional pulsing red ring markers for AI-INFERRED REGIONs.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { ContactShadows, Float } from '@react-three/drei';
import * as THREE from 'three';
import type { RegionPoint } from '../types/vision';

/* ------------------------- textures ------------------------- */

let _skinCache: THREE.CanvasTexture | null = null;

function makeProceduralSkin(): THREE.CanvasTexture {
  if (_skinCache) return _skinCache;
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const ctx = c.getContext('2d') as CanvasRenderingContext2D;
  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0, '#c98a4b');
  grad.addColorStop(0.45, '#a55a2c');
  grad.addColorStop(1, '#7e3a16');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 160; i++) {
    const x = Math.random() * 512;
    const w = 1 + Math.random() * 4;
    const a = 0.04 + Math.random() * 0.1;
    ctx.fillStyle = Math.random() > 0.5 ? `rgba(236,195,150,${a})` : `rgba(70,28,10,${a})`;
    ctx.fillRect(x, Math.random() * 60, w, 512);
  }
  for (let i = 0; i < 900; i++) {
    ctx.fillStyle = `rgba(50,22,10,${0.03 + Math.random() * 0.08})`;
    ctx.fillRect(Math.random() * 512, Math.random() * 512, 1.6, 1.6);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  _skinCache = tex;
  return tex;
}

/** Build a square canvas texture from an image URL (fit-cover crop). */
export function usePhotoTexture(url?: string | null): THREE.CanvasTexture | null {
  const [tex, setTex] = useState<THREE.CanvasTexture | null>(null);
  useEffect(() => {
    if (!url) {
      setTex(null);
      return;
    }
    let alive = true;
    const im = new Image();
    im.onload = () => {
      if (!alive) return;
      const c = document.createElement('canvas');
      c.width = c.height = 1024;
      const g = c.getContext('2d') as CanvasRenderingContext2D;
      const side = Math.min(im.width, im.height);
      g.drawImage(im, (im.width - side) / 2, (im.height - side) / 2, side, side, 0, 0, 1024, 1024);
      const t = new THREE.CanvasTexture(c);
      t.wrapS = THREE.RepeatWrapping;
      t.wrapT = THREE.ClampToEdgeWrapping;
      t.colorSpace = THREE.SRGBColorSpace;
      t.anisotropy = 4;
      if (alive) setTex(t);
    };
    im.src = url;
    return () => {
      alive = false;
    };
  }, [url]);
  return tex;
}

/* ------------------------- geometry ------------------------- */

function useOnionGeometry(): THREE.SphereGeometry {
  return useMemo(() => {
    const geo = new THREE.SphereGeometry(1, 96, 96);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    const uv = geo.attributes.uv as THREE.BufferAttribute;
    const v = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);
      const theta = Math.atan2(v.z, v.x);
      const phi = Math.acos(THREE.MathUtils.clamp(v.y, -1, 1));
      let r = 1;
      r *= 1 + 0.05 * Math.cos(7 * theta) * Math.sin(phi); // vertical ribs
      r *= 1 - 0.16 * Math.pow(Math.max(0, v.y), 2.2); // taper to the neck
      r *= 1 + 0.07 * Math.pow(Math.max(0, -v.y), 2); // basal swell
      v.multiplyScalar(r);
      v.y *= 0.94;
      pos.setXYZ(i, v.x, v.y, v.z);
      // remap u so the photo seam sits at the BACK (u=0.5 => photographed front)
      const u = 0.5 + Math.atan2(v.x, v.z) / (2 * Math.PI);
      uv.setXY(i, u, uv.getY(i));
    }
    geo.computeVertexNormals();
    return geo;
  }, []);
}

/* ------------------------- meshes ------------------------- */

function Bulb({ skin, photo }: { skin: THREE.CanvasTexture; photo: THREE.CanvasTexture | null }) {
  const geo = useOnionGeometry();
  const map = photo ?? skin;
  const materials = useMemo(
    () => ({
      bulb: new THREE.MeshStandardMaterial({
        map,
        bumpMap: skin,
        bumpScale: 0.035,
        roughness: photo ? 0.55 : 0.62,
        metalness: 0.04,
      }),
      shell: new THREE.MeshStandardMaterial({
        map: skin,
        transparent: true,
        opacity: photo ? 0.12 : 0.18,
        roughness: 0.95,
        depthWrite: false,
      }),
    }),
    [map, skin, photo],
  );
  return (
    <group>
      <mesh geometry={geo} material={materials.bulb} castShadow />
      <mesh geometry={geo} material={materials.shell} scale={1.04} />
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

function DamageRing({ pos, delay }: { pos: THREE.Vector3; delay: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const ring = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    const t = state.clock.elapsedTime + delay;
    const pulse = 0.5 + 0.5 * Math.sin(t * 3.2);
    if (ref.current) {
      const m = ref.current.material as THREE.MeshBasicMaterial;
      m.opacity = 0.25 + 0.6 * pulse;
      const s = 1 + 0.22 * pulse;
      ref.current.scale.set(s, s, 1);
    }
    if (ring.current) {
      const m = ring.current.material as THREE.MeshBasicMaterial;
      m.opacity = 0.55 + 0.4 * pulse;
    }
  });
  return (
    <group position={pos}>
      <mesh ref={ring}>
        <torusGeometry args={[0.075, 0.012, 12, 28]} />
        <meshBasicMaterial color="#DC2626" transparent opacity={0.8} />
      </mesh>
      <mesh ref={ref}>
        <circleGeometry args={[0.045, 20]} />
        <meshBasicMaterial color="#EF4444" transparent opacity={0.7} />
      </mesh>
    </group>
  );
}

function DamageMarkers({ damage, modelScale }: { damage: RegionPoint[]; modelScale: number }) {
  const pos = useMemo(
    () =>
      damage.map((d) => {
        const lat = (0.5 - d.y) * Math.PI * 0.92; // y=0.5 => equator
        const lon = (d.x - 0.5) * 2 * Math.PI;
        const R = 1.06 * modelScale;
        return new THREE.Vector3(
          R * Math.cos(lat) * Math.sin(lon),
          R * Math.sin(lat),
          R * Math.cos(lat) * Math.cos(lon),
        );
      }),
    [damage, modelScale],
  );
  return (
    <group>
      {pos.map((p, i) => (
        <DamageRing key={i} pos={p} delay={i * 0.6} />
      ))}
    </group>
  );
}

interface RigApi {
  targets: { rotX: number; rotY: number };
  zoomRef: { current: number };
  dragging: { current: boolean };
}

function Rig({ children, autoRotate, api }: { children: React.ReactNode; autoRotate: boolean; api: RigApi }) {
  const group = useRef<THREE.Group>(null);
  const { camera, pointer } = useThree();
  useFrame((_, delta) => {
    const g = group.current;
    if (!g) return;
    if (autoRotate && !api.dragging.current) api.targets.rotY += delta * 0.22;
    g.rotation.y = THREE.MathUtils.damp(g.rotation.y, api.targets.rotY, 5, delta);
    g.rotation.x = THREE.MathUtils.damp(g.rotation.x, api.targets.rotX, 5, delta);
    if (!api.dragging.current) {
      g.rotation.z = THREE.MathUtils.damp(g.rotation.z, pointer.x * 0.04, 4, delta);
      g.position.y = THREE.MathUtils.damp(g.position.y, pointer.y * 0.05, 4, delta);
    }
    camera.position.z = THREE.MathUtils.damp(camera.position.z, api.zoomRef.current, 5, delta);
  });
  return (
    <group ref={group}>
      <Float speed={1.4} rotationIntensity={0.14} floatIntensity={0.35}>
        {children}
      </Float>
    </group>
  );
}

/* ------------------------- main component ------------------------- */

interface OnionModelProps {
  height?: number;
  textureUrl?: string | null;
  damage?: RegionPoint[];
  autoRotate?: boolean;
  controls?: boolean;
  className?: string;
  modelScale?: number;
}

export default function OnionModel({
  height = 520,
  textureUrl = null,
  damage = [],
  autoRotate = true,
  controls = true,
  className = '',
  modelScale = 1,
}: OnionModelProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const skin = useMemo(() => makeProceduralSkin(), []);
  const photo = usePhotoTexture(textureUrl);

  const targets = useRef({ rotX: 0.12, rotY: 0.4 }).current;
  const zoomRef = useRef(4.7);
  const dragging = useRef(false);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const lastPinch = useRef(0);
  const api = useMemo(() => ({ targets, zoomRef, dragging }), [targets, zoomRef, dragging]);

  const [rotating, setRotating] = useState(autoRotate);
  const [zoomed, setZoomed] = useState(false);

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    dragging.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
  }, []);
  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const p = pointers.current.get(e.pointerId);
      if (!p) return;
      const dx = e.clientX - p.x;
      const dy = e.clientY - p.y;
      p.x = e.clientX;
      p.y = e.clientY;
      if (pointers.current.size === 1) {
        targets.rotY += dx * 0.006;
        targets.rotX = THREE.MathUtils.clamp(targets.rotX + dy * 0.004, -0.6, 0.9);
      } else if (pointers.current.size === 2) {
        const pts = [...pointers.current.values()];
        const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
        if (lastPinch.current) {
          zoomRef.current = THREE.MathUtils.clamp(zoomRef.current - (dist - lastPinch.current) * 0.01, 2.8, 7.5);
        }
        lastPinch.current = dist;
      }
    },
    [targets, zoomRef],
  );
  const endPointer = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    pointers.current.delete(e.pointerId);
    if (pointers.current.size < 2) lastPinch.current = 0;
    if (pointers.current.size === 0) dragging.current = false;
  }, []);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      zoomRef.current = THREE.MathUtils.clamp(zoomRef.current + e.deltaY * 0.002, 2.8, 7.5);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomRef]);

  const reset = () => {
    targets.rotX = 0.12;
    targets.rotY = 0.4;
    zoomRef.current = 4.7;
    setZoomed(false);
    setRotating(autoRotate);
  };

  return (
    <div className={`relative ${className}`} style={{ height }}>
      <div
        ref={wrapRef}
        className="absolute inset-0 cursor-grab touch-none active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endPointer}
        onPointerCancel={endPointer}
      >
        <Canvas shadows camera={{ position: [0, 0.4, 4.7], fov: 42 }} dpr={[1, 1.8]}>
          <ambientLight intensity={0.55} />
          <directionalLight position={[4, 6, 4]} intensity={1.4} color="#fff4e8" castShadow />
          <pointLight position={[-5, 2, -4]} intensity={26} color="#0052ff" distance={14} />
          <pointLight position={[4, -2, -3]} intensity={12} color="#4d7cff" distance={12} />
          <Rig autoRotate={rotating} api={api}>
            <group scale={modelScale}>
              <Bulb skin={skin} photo={photo} />
              <DamageMarkers damage={damage} modelScale={modelScale} />
            </group>
          </Rig>
          <ContactShadows position={[0, -1.45 * modelScale, 0]} opacity={0.32} scale={6} blur={2.6} far={3} color="#1e293b" />
        </Canvas>
      </div>

      {controls && (
        <div className="absolute bottom-3 left-1/2 z-10 flex -translate-x-1/2 gap-2">
          {[
            { k: 'rotate', label: 'ROTATE', on: rotating, act: () => setRotating((v) => !v) },
            {
              k: 'zoom',
              label: 'ZOOM',
              on: zoomed,
              act: () => {
                const nz = !zoomed;
                setZoomed(nz);
                zoomRef.current = nz ? 3.2 : 4.7;
              },
            },
            { k: 'reset', label: 'RESET', on: false, act: reset },
          ].map((b) => (
            <button
              key={b.k}
              onClick={b.act}
              className={`tech-label rounded-full border px-4 py-2 transition-all ${
                b.on
                  ? 'border-electric/60 bg-electric/10 text-electric shadow-glow'
                  : 'border-slate-200 bg-white/85 text-mutext hover:border-electric/40 hover:text-electric'
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
