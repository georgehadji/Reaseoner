'use client';

/* eslint-disable react-hooks/immutability */
/* Three.js imperative graphics require mutation; ref geometry updates are by design */

import { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';

// ─── Constants ───────────────────────────────────────────────────────────────

const NODE_COUNT = 32;
const CONNECTION_DIST = 2.2;
const MAX_CONN = 2;
const MAX_LINES = NODE_COUNT * MAX_CONN;

// Project palette — grayscale only (matches CSS custom properties)
const COLOR_TEXT = new THREE.Color(0.35, 0.35, 0.35);      // #595959
const COLOR_TEXT_MUTED = new THREE.Color(0.28, 0.28, 0.28); // #474747
const COLOR_TEXT_SUBTLE = new THREE.Color(0.22, 0.22, 0.22); // #383838

// ─── Types ───────────────────────────────────────────────────────────────────

interface NodeData {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  phase: number;
  speed: number;
  pulseSpeed: number;
  baseSize: number;
  color: THREE.Color;
}

// ─── Seeded random for deterministic module-level init ───────────────────────

function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function generateNodes(seed = 42): NodeData[] {
  const rand = seededRandom(seed);
  const arr: NodeData[] = [];
  for (let i = 0; i < NODE_COUNT; i++) {
    const colorRoll = rand();
    const color =
      colorRoll < 0.45
        ? COLOR_TEXT.clone()
        : colorRoll < 0.8
          ? COLOR_TEXT_MUTED.clone()
          : COLOR_TEXT_SUBTLE.clone();
    arr.push({
      x: (rand() - 0.5) * 20,
      y: (rand() - 0.5) * 14,
      z: (rand() - 0.5) * 6,
      vx: (rand() - 0.5) * 0.004,
      vy: (rand() - 0.5) * 0.004,
      vz: (rand() - 0.5) * 0.002,
      phase: rand() * Math.PI * 2,
      speed: 0.15 + rand() * 0.35,
      pulseSpeed: 0.8 + rand() * 1.5,
      baseSize: 2.5 + rand() * 3.5,
      color,
    });
  }
  return arr;
}

// Module-level constant avoids render-phase impurity rules
const NODES = generateNodes();

// ─── Geometry Helpers ────────────────────────────────────────────────────────

function initParticleGeo(nodes: NodeData[]): THREE.BufferGeometry {
  const geo = new THREE.BufferGeometry();
  const positions = new Float32Array(NODE_COUNT * 3);
  const colors = new Float32Array(NODE_COUNT * 3);
  const sizes = new Float32Array(NODE_COUNT);

  for (let i = 0; i < NODE_COUNT; i++) {
    const n = nodes[i];
    positions[i * 3] = n.x;
    positions[i * 3 + 1] = n.y;
    positions[i * 3 + 2] = n.z;
    colors[i * 3] = n.color.r;
    colors[i * 3 + 1] = n.color.g;
    colors[i * 3 + 2] = n.color.b;
    sizes[i] = n.baseSize;
  }

  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
  return geo;
}

function initLineGeo(): THREE.BufferGeometry {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX_LINES * 2 * 3), 3));
  geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(MAX_LINES * 2 * 3), 3));
  geo.setDrawRange(0, 0);
  return geo;
}

function createMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      uPixelRatio: { value: 1 },
      uTime: { value: 0 },
    },
    vertexShader: `
      attribute float size;
      attribute vec3 color;
      varying vec3 vColor;
      varying float vAlpha;
      uniform float uPixelRatio;
      uniform float uTime;

      void main() {
        vColor = color;
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        float pulse = 1.0 + 0.15 * sin(uTime * 1.5 + position.x * 0.5 + position.y * 0.3);
        gl_PointSize = size * pulse * uPixelRatio * (120.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
        vAlpha = smoothstep(12.0, 4.0, -mvPosition.z);
      }
    `,
    fragmentShader: `
      varying vec3 vColor;
      varying float vAlpha;

      void main() {
        vec2 coord = gl_PointCoord - vec2(0.5);
        float dist = length(coord);
        if (dist > 0.5) discard;
        float strength = 1.0 - smoothstep(0.38, 0.5, dist);
        float glow = 1.0 - smoothstep(0.0, 0.48, dist);
        vec3 finalColor = vColor * (strength * 0.5 + glow * 0.15);
        float finalAlpha = (strength * 0.4 + glow * 0.12) * vAlpha;
        gl_FragColor = vec4(finalColor, finalAlpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}

// ─── Inner Scene Component ───────────────────────────────────────────────────

function ConstellationScene() {
  const pointsRef = useRef<THREE.Points>(null);
  const linesRef = useRef<THREE.LineSegments>(null);
  const mouseRef = useRef({ x: 0, y: 0, tx: 0, ty: 0 });
  const reducedRef = useRef(false);

  const particleGeo = useMemo(() => initParticleGeo(NODES), []);
  const lineGeo = useMemo(() => initLineGeo(), []);
  const material = useMemo(() => createMaterial(), []);

  useEffect(() => {
    reducedRef.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const onMove = (e: MouseEvent) => {
      mouseRef.current.tx = (e.clientX / window.innerWidth) * 2 - 1;
      mouseRef.current.ty = -(e.clientY / window.innerHeight) * 2 + 1;
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, []);

  useFrame((state) => {
    const elapsed = state.clock.getElapsedTime();
    const points = pointsRef.current;
    const lines = linesRef.current;
    if (!points || !lines) return;

    const posAttr = particleGeo.attributes.position as THREE.BufferAttribute;
    const reduced = reducedRef.current;
    const mouse = mouseRef.current;

    mouse.x += (mouse.tx - mouse.x) * 0.04;
    mouse.y += (mouse.ty - mouse.y) * 0.04;

    if (!reduced) {
      for (let i = 0; i < NODE_COUNT; i++) {
        const n = NODES[i];
        const t = elapsed * n.speed;
        n.x += Math.sin(t + n.phase) * 0.0015 + n.vx;
        n.y += Math.cos(t * 0.8 + n.phase) * 0.0012 + n.vy;
        n.z += Math.sin(t * 0.5 + n.phase) * 0.0008 + n.vz;
        n.x += (mouse.x * 0.2 - n.x * 0.01) * 0.002;
        n.y += (mouse.y * 0.15 - n.y * 0.01) * 0.002;

        if (n.x > 11) n.x = -11;
        if (n.x < -11) n.x = 11;
        if (n.y > 8) n.y = -8;
        if (n.y < -8) n.y = 8;
        if (n.z > 4) n.z = -4;
        if (n.z < -4) n.z = 4;

        posAttr.setXYZ(i, n.x, n.y, n.z);
      }
      posAttr.needsUpdate = true;
    }

    material.uniforms.uTime.value = elapsed;
    material.uniforms.uPixelRatio.value = state.gl.getPixelRatio();

    const linePos = lineGeo.attributes.position as THREE.BufferAttribute;
    const lineCol = lineGeo.attributes.color as THREE.BufferAttribute;
    let lineIdx = 0;

    for (let i = 0; i < NODE_COUNT; i++) {
      let connections = 0;
      const ni = NODES[i];
      for (let j = i + 1; j < NODE_COUNT; j++) {
        if (connections >= MAX_CONN) break;
        const nj = NODES[j];
        const dx = ni.x - nj.x;
        const dy = ni.y - nj.y;
        const dz = ni.z - nj.z;
        const distSq = dx * dx + dy * dy + dz * dz;
        if (distSq < CONNECTION_DIST * CONNECTION_DIST) {
          const dist = Math.sqrt(distSq);
          const alpha = 1.0 - dist / CONNECTION_DIST;
          const fade = 0.12 + 0.06 * Math.sin(elapsed * 0.5 + ni.phase);
          const a = Math.max(0, alpha * fade);

          linePos.setXYZ(lineIdx * 2, ni.x, ni.y, ni.z);
          linePos.setXYZ(lineIdx * 2 + 1, nj.x, nj.y, nj.z);

          const gray = (ni.color.r + nj.color.r) * 0.5 * a;
          const r = gray;
          const g = gray;
          const b = gray;

          lineCol.setXYZ(lineIdx * 2, r, g, b);
          lineCol.setXYZ(lineIdx * 2 + 1, r, g, b);
          lineIdx++;
          connections++;
        }
      }
    }

    lineGeo.setDrawRange(0, lineIdx * 2);
    linePos.needsUpdate = true;
    lineCol.needsUpdate = true;
  });

  return (
    <>
      <points ref={pointsRef} geometry={particleGeo} material={material} />
      <lineSegments ref={linesRef} geometry={lineGeo}>
        <lineBasicMaterial
          vertexColors
          transparent
          opacity={1}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </lineSegments>
    </>
  );
}

// ─── Exported Canvas Wrapper ─────────────────────────────────────────────────

export function NeuralConstellation({ className }: { className?: string }) {
  return (
    <div className={className} aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 9], fov: 55, near: 0.1, far: 25 }}
        dpr={[1, 1.5]}
        gl={{
          antialias: false,
          alpha: true,
          powerPreference: 'high-performance',
        }}
        style={{ background: 'transparent' }}
      >
        <ConstellationScene />
        <EffectComposer>
          <Bloom
            luminanceThreshold={0.8}
            luminanceSmoothing={0.9}
            intensity={0.25}
            mipmapBlur
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
