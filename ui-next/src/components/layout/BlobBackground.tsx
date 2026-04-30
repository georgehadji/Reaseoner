'use client';

interface BlobBackgroundProps {
  /** When true, the background becomes visibly more energetic. */
  active?: boolean;
}

/**
 * Organic blob background that intensifies when the reasoning pipeline is active.
 *
 * Base blobs drift slowly. When `active` is true:
 * - Blobs brighten and grow via smooth CSS transitions
 * - An additional energy layer fades in with faster pulse
 * - A top glow bar appears
 *
 * No animation-name switching — the underlying drift never resets.
 */
export function BlobBackground({ active = false }: BlobBackgroundProps) {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      aria-hidden="true"
    >
      {/* ── Base blob layer ─────────────────────────────── */}
      <div
        className="blob-1 absolute"
        style={{
          width: '70vw',
          height: '70vw',
          maxWidth: 1000,
          maxHeight: 1000,
          top: '-20%',
          right: '-15%',
          background: 'radial-gradient(circle, rgba(128,128,128,0.06) 0%, rgba(128,128,128,0.02) 45%, transparent 70%)',
          filter: 'blur(80px)',
          borderRadius: '60% 40% 50% 50% / 50% 60% 40% 50%',
          opacity: active ? 1 : 0.6,
          transform: active ? 'scale(1.15)' : 'scale(1)',
          transition: 'opacity 1s ease, transform 1s ease',
          willChange: 'transform',
        }}
      />

      <div
        className="blob-2 absolute"
        style={{
          width: '60vw',
          height: '60vw',
          maxWidth: 900,
          maxHeight: 900,
          bottom: '-15%',
          left: '-20%',
          background: 'radial-gradient(circle, rgba(160,160,160,0.04) 0%, rgba(160,160,160,0.01) 45%, transparent 70%)',
          filter: 'blur(100px)',
          borderRadius: '40% 60% 50% 50% / 60% 40% 60% 40%',
          opacity: active ? 1 : 0.55,
          transform: active ? 'scale(1.15)' : 'scale(1)',
          transition: 'opacity 1s ease, transform 1s ease',
          willChange: 'transform',
        }}
      />

      <div
        className="blob-3 absolute"
        style={{
          width: '50vw',
          height: '50vw',
          maxWidth: 800,
          maxHeight: 800,
          bottom: '5%',
          left: '25%',
          background: 'radial-gradient(circle, rgba(112,112,112,0.03) 0%, transparent 60%)',
          filter: 'blur(120px)',
          borderRadius: '50% 50% 40% 60% / 40% 50% 60% 50%',
          opacity: active ? 1 : 0.5,
          transform: active ? 'scale(1.2)' : 'scale(1)',
          transition: 'opacity 1s ease, transform 1s ease',
        }}
      />

      {/* ── Intensity overlay (fades in when active) ────── */}
      <div
        className="absolute inset-0"
        style={{
          opacity: active ? 1 : 0,
          transition: 'opacity 1.2s ease',
        }}
      >
        {/* Brighter blue blob */}
        <div
          className="blob-intense-1 absolute"
          style={{
            width: '55vw',
            height: '55vw',
            maxWidth: 800,
            maxHeight: 800,
            top: '-10%',
            right: '-5%',
            background: 'radial-gradient(circle, rgba(128,128,128,0.07) 0%, rgba(128,128,128,0.02) 40%, transparent 65%)',
            filter: 'blur(70px)',
            borderRadius: '55% 45% 50% 50% / 50% 55% 45% 50%',
            willChange: 'transform',
          }}
        />

        {/* Brighter cyan blob */}
        <div
          className="blob-intense-2 absolute"
          style={{
            width: '50vw',
            height: '50vw',
            maxWidth: 750,
            maxHeight: 750,
            bottom: '-10%',
            left: '-10%',
            background: 'radial-gradient(circle, rgba(160,160,160,0.06) 0%, rgba(160,160,160,0.02) 40%, transparent 65%)',
            filter: 'blur(80px)',
            borderRadius: '45% 55% 50% 50% / 55% 45% 55% 45%',
            willChange: 'transform',
          }}
        />

        {/* Pulsing energy centre */}
        <div
          className="blob-pulse absolute"
          style={{
            width: '40vw',
            height: '40vw',
            maxWidth: 600,
            maxHeight: 600,
            top: '20%',
            left: '30%',
            background: 'radial-gradient(circle, rgba(128,128,128,0.04) 0%, transparent 55%)',
            filter: 'blur(60px)',
            borderRadius: '50%',
            willChange: 'transform, opacity',
          }}
        />
      </div>

      {/* ── Top glow bar (active only) ──────────────────── */}
      <div
        className="absolute left-0 right-0 top-0 h-px"
        style={{
          opacity: active ? 1 : 0,
          transition: 'opacity 0.8s ease',
          background: 'linear-gradient(90deg, transparent 0%, rgba(160,160,160,0.15) 50%, transparent 100%)',
          boxShadow: active ? '0 0 40px 2px rgba(160,160,160,0.07)' : 'none',
          transitionProperty: 'opacity, box-shadow',
          transitionDuration: '0.8s',
          transitionTimingFunction: 'ease',
        }}
      />

      {/* ── Vignette overlay ────────────────────────────── */}
      <div
        className="absolute inset-0"
        style={{
          background: active
            ? 'radial-gradient(ellipse 75% 55% at 50% 35%, transparent 25%, var(--bg) 80%)'
            : 'radial-gradient(ellipse 80% 60% at 50% 40%, transparent 30%, var(--bg) 85%)',
          transition: 'background 1s ease',
        }}
      />
    </div>
  );
}
