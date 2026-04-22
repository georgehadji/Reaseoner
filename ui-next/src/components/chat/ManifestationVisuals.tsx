'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';

interface ManifestationVisualsProps {
  progress: number; // 0 to 1
}

export function ManifestationVisuals({ progress }: ManifestationVisualsProps) {
  // Determine state based on progress
  const isDissolved = progress < 0.3;
  const isCoalescing = progress >= 0.3 && progress < 0.7;
  const isStabilizing = progress >= 0.7;

  return (
    <div className="relative flex h-64 w-full items-center justify-center overflow-hidden rounded-[24px] bg-black/5 selection:bg-none">
      <AnimatePresence mode="wait">
        {/* Stage 1: Dissolved (0-30%) */}
        {isDissolved && (
          <motion.div
            key="dissolved"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, filter: 'blur(20px)' }}
            className="absolute inset-0 flex items-center justify-center"
          >
            {/* Grain/Mist Overlay */}
            <div className="absolute inset-0 opacity-20 [mask-image:radial-gradient(circle,white,transparent_70%)]">
              {/* Noise texture simulated with CSS for zero external deps */}
              <div
                className="h-full w-full opacity-50"
                style={{
                  backgroundImage: `url('data:image/svg+xml,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)"/%3E%3C/svg%3E')`,
                }}
              />
            </div>

            {/* Fast moving light blobs */}
            {[...Array(5)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute h-32 w-32 rounded-full bg-gradient-to-r from-sky-400/30 to-amber-300/30 blur-3xl"
                animate={{
                  x: [Math.random() * 200 - 100, Math.random() * 200 - 100],
                  y: [Math.random() * 200 - 100, Math.random() * 200 - 100],
                  scale: [1, 1.5, 0.8],
                  opacity: [0.3, 0.6, 0.3],
                }}
                transition={{
                  duration: 2 + i,
                  repeat: Infinity,
                  repeatType: 'reverse',
                }}
              />
            ))}
            <div className="text-xs font-medium uppercase tracking-[0.4em] text-sky-400/60 mix-blend-color-dodge">
              Gathering Ether...
            </div>
          </motion.div>
        )}

        {/* Stage 2: Coalescing (30-70%) */}
        {isCoalescing && (
          <motion.div
            key="coalescing"
            initial={{ opacity: 0, scale: 0.9, filter: 'blur(10px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 flex items-center justify-center"
          >
            {/* Ripple Effects */}
            {[...Array(3)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute rounded-full border border-white/30"
                animate={{
                  width: ['0%', '150%'],
                  height: ['0%', '150%'],
                  opacity: [0.5, 0],
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  delay: i * 1,
                  ease: 'easeOut',
                }}
              />
            ))}

            {/* Placeholder Silhouette */}
            <motion.div
              className="relative z-10 h-40 w-40 rounded-[32px] bg-gradient-to-br from-white/10 to-white/5 shadow-2xl backdrop-blur-sm"
              animate={{
                boxShadow: [
                  '0 0 20px rgba(56, 189, 248, 0.1)',
                  '0 0 40px rgba(245, 158, 11, 0.15)',
                  '0 0 20px rgba(56, 189, 248, 0.1)',
                ],
              }}
              transition={{ duration: 4, repeat: Infinity }}
            >
              <div className="absolute inset-0 flex items-center justify-center overflow-hidden rounded-[32px]">
                <div className="h-full w-full bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.05)_50%,transparent_75%)] bg-[length:250%_250%] animate-pulse" />
                <Sparkles className="h-10 w-10 text-white/20" />
              </div>
            </motion.div>

            <div className="absolute bottom-6 text-[10px] font-semibold uppercase tracking-[0.25em] text-amber-500/60">
              Coalescing Structure
            </div>
          </motion.div>
        )}

        {/* Stage 3: Stabilizing (70-100%) */}
        {isStabilizing && (
          <motion.div
            key="stabilizing"
            initial={{ opacity: 0, scale: 1.1 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute inset-0 flex items-center justify-center"
          >
            {/* Sharpening effect frame */}
            <motion.div
              className="relative h-48 w-48 rounded-[28px] border border-white/40 bg-white/20 p-1 shadow-[0_0_50px_rgba(255,255,255,0.2)] backdrop-blur-md"
              animate={{
                scale: [1, 1.01, 1],
              }}
              transition={{ duration: 0.5, repeat: Infinity }}
            >
              <div className="h-full w-full rounded-[24px] bg-gradient-to-tr from-sky-100/20 to-amber-50/20" />

              {/* The "Pop" - flash of light at near-completion */}
              {progress > 0.95 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: [0, 1, 0], scale: [0, 1.5, 2] }}
                  transition={{ duration: 0.6 }}
                  className="absolute inset-0 rounded-full bg-white blur-2xl"
                />
              )}
            </motion.div>

            <motion.div
              className="absolute bottom-10 flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-sky-400"
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              Stabilizing Frequency
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
