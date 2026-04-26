'use client';

import { useEffect, useRef } from 'react';

interface ParticleNode {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  radius: number;
}

const NODE_COUNT = 80;
const MAX_DIST = 180;
const MOUSE_RADIUS = 220;

export function ThreeBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -9999, y: -9999 });
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Use a non-null alias so TypeScript doesn't lose track in closures
    const c: CanvasRenderingContext2D = ctx;

    let W = window.innerWidth;
    let H = window.innerHeight;
    canvas.width = W;
    canvas.height = H;

    const nodes: ParticleNode[] = Array.from({ length: NODE_COUNT }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      z: Math.random(),
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      vz: (Math.random() - 0.5) * 0.002,
      radius: Math.random() * 1.8 + 0.6,
    }));

    function onMouseMove(e: MouseEvent) {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    }

    function onResize() {
      W = window.innerWidth;
      H = window.innerHeight;
      canvas!.width = W;
      canvas!.height = H;
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('resize', onResize, { passive: true });

    function draw() {
      c.clearRect(0, 0, W, H);

      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.z += n.vz;
        if (n.z < 0) { n.z = 0; n.vz *= -1; }
        if (n.z > 1) { n.z = 1; n.vz *= -1; }

        if (n.x < -20) n.x = W + 20;
        if (n.x > W + 20) n.x = -20;
        if (n.y < -20) n.y = H + 20;
        if (n.y > H + 20) n.y = -20;

        // Mouse repulsion
        const dx = n.x - mx;
        const dy = n.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MOUSE_RADIUS && dist > 0) {
          const force = ((MOUSE_RADIUS - dist) / MOUSE_RADIUS) * 0.6;
          n.vx += (dx / dist) * force * 0.04;
          n.vy += (dy / dist) * force * 0.04;
        }

        n.vx *= 0.992;
        n.vy *= 0.992;
      }

      // Connections
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < MAX_DIST) {
            const t = 1 - d / MAX_DIST;
            const depth = (a.z + b.z) * 0.5;
            const alpha = t * t * 0.55 * (0.3 + depth * 0.7);
            c.beginPath();
            c.moveTo(a.x, a.y);
            c.lineTo(b.x, b.y);
            c.strokeStyle = `rgba(0, 201, 177, ${alpha})`;
            c.lineWidth = t * 0.9;
            c.stroke();
          }
        }
      }

      // Nodes
      for (const n of nodes) {
        const brightness = 0.4 + n.z * 0.6;
        const r = n.radius * (0.6 + n.z * 0.4);

        const grad = c.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 4.5);
        grad.addColorStop(0, `rgba(0, 201, 177, ${0.25 * brightness})`);
        grad.addColorStop(1, 'rgba(0, 201, 177, 0)');
        c.beginPath();
        c.arc(n.x, n.y, r * 4.5, 0, Math.PI * 2);
        c.fillStyle = grad;
        c.fill();

        c.beginPath();
        c.arc(n.x, n.y, r, 0, Math.PI * 2);
        c.fillStyle = n.z > 0.6
          ? `rgba(245, 158, 11, ${0.6 + n.z * 0.4})`
          : `rgba(0, 201, 177, ${0.6 + n.z * 0.4})`;
        c.fill();
      }

      rafRef.current = requestAnimationFrame(draw);
    }

    rafRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 z-0"
      aria-hidden="true"
      style={{ opacity: 0.55 }}
    />
  );
}
