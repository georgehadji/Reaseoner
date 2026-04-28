'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface ManifestationVisualsProps {
  progress: number; // 0 to 1
}

export function ManifestationVisuals({ progress }: ManifestationVisualsProps) {
  return (
    <div
      className="relative h-52 w-full overflow-hidden rounded-lg"
      style={{
        background: 'var(--surface-3)',
        border: '1px solid var(--border-strong)',
      }}
    >
      {/* Dot grid */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'radial-gradient(circle, rgba(0,201,177,0.12) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
          opacity: 0.6,
        }}
      />

      {/* Progress fill — rises from bottom */}
      <motion.div
        className="absolute bottom-0 left-0 right-0"
        style={{
          background:
            'linear-gradient(to top, rgba(0,201,177,0.07) 0%, transparent 100%)',
        }}
        animate={{ height: `${progress * 100}%` }}
        transition={{ duration: 0.4, ease: 'linear' }}
      />

      {/* Scan line */}
      <motion.div
        className="absolute left-0 right-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, rgba(0,201,177,0.6) 20%, var(--accent) 50%, rgba(0,201,177,0.6) 80%, transparent 100%)',
          boxShadow: '0 0 8px 1px rgba(0,201,177,0.3)',
        }}
        animate={{ top: ['0%', '100%'] }}
        transition={{ duration: 2.8, repeat: Infinity, ease: 'linear' }}
      />

      {/* Corner markers */}
      {[
        { top: 10, left: 10, rotate: 0 },
        { top: 10, right: 10, rotate: 90 },
        { bottom: 10, right: 10, rotate: 180 },
        { bottom: 10, left: 10, rotate: 270 },
      ].map((pos, i) => (
        <div
          key={i}
          className="absolute h-4 w-4"
          style={{
            ...pos,
            rotate: `${pos.rotate}deg`,
            opacity: 0.35,
          }}
        >
          <div
            className="absolute top-0 left-0 h-px w-3"
            style={{ background: 'var(--accent)' }}
          />
          <div
            className="absolute top-0 left-0 h-3 w-px"
            style={{ background: 'var(--accent)' }}
          />
        </div>
      ))}

      {/* Center — pulsing dot with rings */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative flex items-center justify-center">
          {/* Rings */}
          {[0, 0.6, 1.2].map((delay, i) => (
            <motion.div
              key={i}
              className="absolute rounded-full"
              style={{ border: '1px solid rgba(0,201,177,0.35)' }}
              initial={{ width: 12, height: 12, opacity: 0.5 }}
              animate={{ width: 56, height: 56, opacity: 0 }}
              transition={{
                duration: 2.4,
                repeat: Infinity,
                delay,
                ease: 'easeOut',
              }}
            />
          ))}

          {/* Core dot */}
          <motion.div
            className="relative z-10 h-2 w-2 rounded-full"
            style={{ background: 'var(--accent)' }}
            animate={{ opacity: [0.6, 1, 0.6] }}
            transition={{ duration: 1.8, repeat: Infinity }}
          />
        </div>
      </div>
    </div>
  );
}
