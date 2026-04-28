'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';

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
  uniform vec2 uMouse;
  uniform float uClickTime;
  uniform vec2 uClickPos;
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
    float t = uTime * 0.03 * uMotion;

    // Mouse parallax: subtle shift opposite to cursor
    vec2 mouseOffset = (uMouse - 0.5) * 0.12;
    uv += mouseOffset;

    // Slow nebula drift
    vec2 p = uv * 2.5;
    p.x += t * 0.3;
    p.y += t * 0.1;

    float n1 = fbm(p + vec2(t * 0.2, 0.0));
    float n2 = fbm(p * 1.3 + vec2(0.0, t * 0.15) + 10.0);
    float n3 = fbm(p * 0.7 + vec2(t * 0.1, t * 0.25) + 20.0);

    // Click ripple distortion
    float clickAge = uTime - uClickTime;
    float ripple = 0.0;
    if (clickAge > 0.0 && clickAge < 3.0) {
      float dist = length(vUv - uClickPos);
      float wave = sin(dist * 30.0 - clickAge * 12.0);
      float envelope = exp(-clickAge * 1.5) * smoothstep(0.0, 0.5, clickAge);
      float radiusMask = smoothstep(0.0, 0.6, dist) * (1.0 - smoothstep(0.6, 1.0, dist));
      ripple = wave * envelope * radiusMask * 0.15;
    }
    n1 += ripple;
    n2 += ripple * 0.7;

    // Teal (#00C9B1) → deep navy base
    vec3 teal = vec3(0.0, 0.788, 0.694);
    vec3 navy = vec3(0.024, 0.043, 0.063);
    vec3 amber = vec3(0.961, 0.620, 0.043);

    vec3 col = navy;
    col = mix(col, teal * 0.35, smoothstep(-0.3, 0.6, n1) * 0.4);
    col = mix(col, teal * 0.25, smoothstep(-0.2, 0.7, n2) * 0.3);
    col = mix(col, amber * 0.20, smoothstep(0.0, 0.8, n3) * 0.15);

    // Subtle vignette
    float vignette = 1.0 - smoothstep(0.4, 1.2, length(vUv - 0.5) * 1.4);
    col *= 0.85 + vignette * 0.15;

    gl_FragColor = vec4(col, 1.0);
  }
`;

export function NebulaBackground() {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const motionScale = prefersReducedMotion ? 0.0 : 1.0;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Interaction state
    const mouse = { x: 0.5, y: 0.5, targetX: 0.5, targetY: 0.5 };
    const click = { time: -100.0, x: 0.5, y: 0.5 };

    // Shader material
    const uniforms = {
      uTime: { value: 0.0 },
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
      uMotion: { value: motionScale },
      uMouse: { value: new THREE.Vector2(0.5, 0.5) },
      uClickTime: { value: -100.0 },
      uClickPos: { value: new THREE.Vector2(0.5, 0.5) },
    };

    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms,
    });

    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Event handlers
    function onMouseMove(e: MouseEvent) {
      mouse.targetX = e.clientX / window.innerWidth;
      mouse.targetY = 1.0 - e.clientY / window.innerHeight; // flip Y for shader
    }

    function onClick(e: MouseEvent) {
      click.time = uniforms.uTime.value;
      click.x = e.clientX / window.innerWidth;
      click.y = 1.0 - e.clientY / window.innerHeight;
      uniforms.uClickTime.value = click.time;
      uniforms.uClickPos.value.set(click.x, click.y);
    }

    function onTouchMove(e: TouchEvent) {
      if (e.touches.length > 0) {
        mouse.targetX = e.touches[0].clientX / window.innerWidth;
        mouse.targetY = 1.0 - e.touches[0].clientY / window.innerHeight;
      }
    }

    function onTouchStart(e: TouchEvent) {
      if (e.touches.length > 0) {
        click.time = uniforms.uTime.value;
        click.x = e.touches[0].clientX / window.innerWidth;
        click.y = 1.0 - e.touches[0].clientY / window.innerHeight;
        uniforms.uClickTime.value = click.time;
        uniforms.uClickPos.value.set(click.x, click.y);
      }
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('click', onClick);
    window.addEventListener('touchmove', onTouchMove, { passive: true });
    window.addEventListener('touchstart', onTouchStart, { passive: true });

    // Animation
    let rafId = 0;
    const startTime = performance.now();

    function animate() {
      rafId = requestAnimationFrame(animate);
      uniforms.uTime.value = (performance.now() - startTime) / 1000;

      // Smooth mouse lerp (damping)
      mouse.x += (mouse.targetX - mouse.x) * 0.04;
      mouse.y += (mouse.targetY - mouse.y) * 0.04;
      uniforms.uMouse.value.set(mouse.x, mouse.y);

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

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('click', onClick);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('touchstart', onTouchStart);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-0"
      aria-hidden="true"
      style={{ opacity: 0.9 }}
    />
  );
}
