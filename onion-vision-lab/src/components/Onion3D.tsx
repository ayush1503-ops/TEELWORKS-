import { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';

/** deterministic pseudo-noise so SSR-free render is stable */
function noise3(x: number, y: number, z: number): number {
  const s = Math.sin(x * 12.9898 + y * 78.233 + z * 37.719) * 43758.5453;
  return (s - Math.floor(s)) * 2 - 1;
}

function OnionMesh({ scale = 1, status = 'GREEN', hotspots = [] as { x: number; y: number }[] }: {
  scale?: number;
  status?: 'GREEN' | 'YELLOW' | 'RED';
  hotspots?: { x: number; y: number }[];
}) {
  const group = useRef<THREE.Group>(null);
  const geometry = useMemo(() => {
    const geo = new THREE.IcosahedronGeometry(1, 24);
    const pos = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      const n = noise3(x * 2.2 + 10, y * 2.2, z * 2.2) * 0.045;
      const squash = y > 0 ? 1 - 0.18 * y : 1;
      const r = 1 + n;
      pos.setXYZ(i, x * r, y * r * squash * 0.92 + 0.04, z * r);
    }
    geo.computeVertexNormals();
    return geo;
  }, []);

  const color = status === 'RED' ? '#8b4fc9' : status === 'YELLOW' ? '#7c5cd6' : '#6d4bd0';

  useFrame((state) => {
    if (group.current) group.current.rotation.y = state.clock.elapsedTime * 0.25;
  });

  return (
    <group ref={group} scale={scale}>
      <mesh geometry={geometry} castShadow>
        <meshStandardMaterial color={color} roughness={0.62} metalness={0.08} />
      </mesh>
      {/* papery outer skin hint */}
      <mesh scale={1.035}>
        <icosahedronGeometry args={[1, 3]} />
        <meshBasicMaterial color="#c4b5fd" wireframe transparent opacity={0.07} />
      </mesh>
      {/* sprout tip */}
      <mesh position={[0, 1.02, 0]}>
        <coneGeometry args={[0.13, 0.34, 8]} />
        <meshStandardMaterial color="#86efac" roughness={0.5} />
      </mesh>
      {hotspots.map((h, i) => (
        <HotspotMesh key={i} x={h.x} y={h.y} delay={i * 0.7} />
      ))}
    </group>
  );
}

function HotspotMesh({ x, y, delay }: { x: number; y: number; delay: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const px = (x - 0.5) * 1.35;
  const py = (0.5 - y) * 1.15;
  useFrame((state) => {
    const t = state.clock.elapsedTime + delay;
    const s = 1 + 0.35 * Math.sin(t * 3);
    ref.current?.scale.setScalar(s);
    const m = ref.current?.material as THREE.MeshBasicMaterial | undefined;
    if (m) m.opacity = 0.55 + 0.4 * Math.sin(t * 3);
  });
  return (
    <mesh ref={ref} position={[px, py, 0.72]}>
      <sphereGeometry args={[0.075, 16, 16]} />
      <meshBasicMaterial color="#f87171" transparent opacity={0.8} />
    </mesh>
  );
}

export function Hero3D() {
  return (
    <div className="absolute inset-0">
      <Canvas camera={{ position: [0, 0.3, 3.4], fov: 42 }} dpr={[1, 1.6]}>
        <ambientLight intensity={0.55} />
        <directionalLight position={[3, 4, 2]} intensity={1.1} />
        <pointLight position={[-3, -1, 2]} intensity={0.5} color="#a78bfa" />
        <Float speed={1.6} rotationIntensity={0.25} floatIntensity={0.9}>
          <OnionMesh scale={1.15} />
        </Float>
      </Canvas>
    </div>
  );
}

export function Inspection3D({ status, regions }: {
  status: 'GREEN' | 'YELLOW' | 'RED';
  regions: { x: number; y: number }[];
}) {
  const hs = regions.length > 0 ? regions : [];
  return (
    <div className="absolute inset-0">
      <Canvas camera={{ position: [0, 0.2, 3.2], fov: 42 }} dpr={[1, 1.6]}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[3, 4, 3]} intensity={1.15} />
        <pointLight position={[-2.5, -1.5, 2]} intensity={0.45} color="#a78bfa" />
        <Float speed={1.2} rotationIntensity={0.15} floatIntensity={0.5}>
          <OnionMesh scale={1.25} status={status} hotspots={hs} />
        </Float>
      </Canvas>
    </div>
  );
}
