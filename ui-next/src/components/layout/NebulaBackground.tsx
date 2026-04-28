'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { DEFAULT_ACCENT_RGB, type MethodId, METHOD_ACCENT_RGB } from '@/lib/method-colors';

const VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`;

const FRAGMENT_SHADER = /* glsl */ `
  uniform float uTime;
  uniform vec2 uResolution;
  uniform float uMotion;
  uniform vec3 uAccent;
  varying vec2 vUv;

  // Simplex 2D noise
  vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }

  float snoise(vec2 v){
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                        -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy));
    vec2 x0 = v -   i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod(i, 289.0);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 ))
      + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
      dot(x12.zw,x12.zw)), 0.0);
    m = m*m;
    m = m*m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 5; i++) {
      value += amplitude * snoise(p);
      p *= 2.0;
      amplitude *= 0.5;
    }
    return value;
  }

  void main() {
    vec2 uv = vUv;
    // Very slow time — barely perceptible drift
    float t = uTime * 0.015 * uMotion;

    vec2 p = uv * 2.5;
    p.x += t * 0.15;
    p.y += t * 0.05;

    float n1 = fbm(p + vec2(t * 0.1, 0.0));
    float n2 = fbm(p * 1.3 + vec2(0.0, t * 0.08) + 10.0);
    float n3 = fbm(p * 0.7 + vec2(t * 0.05, t * 0.12) + 20.0);

    // Deep carbon base
    vec3 carbon = vec3(0.016, 0.031, 0.047);
    vec3 coolAmber = vec3(0.957, 0.643, 0.231);

    // Subtle nebula — low intensity for readability
    vec3 col = carbon;
    col = mix(col, uAccent * 0.28, smoothstep(-0.3, 0.6, n1) * 0.35);
    col = mix(col, uAccent * 0.18, smoothstep(-0.2, 0.7, n2) * 0.25);
    col = mix(col, coolAmber * 0.10, smoothstep(0.0, 0.8, n3) * 0.08);

    // Subtle vignette for depth
    float vignette = 1.0 - smoothstep(0.4, 1.2, length(vUv - 0.5) * 1.4);
    col *= 0.88 + vignette * 0.12;

    gl_FragColor = vec4(col, 1.0);
  }
`;

interface NebulaBackgroundProps {
  /** Active reasoning method — drives nebula accent color. */
  method?: MethodId | null;
}

export function NebulaBackground({ method }: NebulaBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const motionScale = prefersReducedMotion ? 0.0 : 1.0;

    // Scene setup — no bloom, simple direct render
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';
    container.appendChild(renderer.domElement);

    // Color state — smooth transition
    const targetAccent = new THREE.Vector3(...DEFAULT_ACCENT_RGB);
    const currentAccent = new THREE.Vector3(...DEFAULT_ACCENT_RGB);

    // Shader material
    const uniforms = {
      uTime: { value: 0.0 },
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      uMotion: { value: motionScale },
      uAccent: { value: currentAccent },
    };

    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms,
    });

    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Animation — very low frame rate feel via longer intervals
    let rafId = 0;
    const startTime = performance.now();

    function animate() {
      rafId = requestAnimationFrame(animate);
      uniforms.uTime.value = (performance.now() - startTime) / 1000;

      // Smooth accent color transition
      currentAccent.lerp(targetAccent, 0.012);

      renderer.render(scene, camera);
    }

    if (motionScale > 0) {
      animate();
    } else {
      renderer.render(scene, camera);
    }

    // Resize handler
    function onResize() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      renderer.setSize(w, h);
      uniforms.uResolution.value.set(w, h);
      if (motionScale === 0) renderer.render(scene, camera);
    }

    window.addEventListener('resize', onResize);

    // Expose color updater for React prop changes
    function updateMethodColor() {
      const rgb = method ? METHOD_ACCENT_RGB[method] : DEFAULT_ACCENT_RGB;
      targetAccent.set(rgb[0], rgb[1], rgb[2]);
    }
    updateMethodColor();

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', onResize);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [method]);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-0"
      aria-hidden="true"
      style={{ opacity: 0.85 }}
    />
  );
}
