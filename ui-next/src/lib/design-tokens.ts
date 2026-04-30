/**
 * Reasoner Design System Tokens
 * Single Source of Truth for colors, typography, and spacing.
 */

export const reasonerTokens = {
  brand: {
    name: 'Reasoner',
    version: '1.0.0',
  },
  colors: {
    // Shared functional colors
    common: {
      white: '#FFFFFF',
      black: '#000000',
      transparent: 'transparent',
    },
    // Dark Theme (Security Edition)
    dark: {
      bg: '#04080C',
      surface: '#0A0F16',
      surface2: '#0E141D',
      surface3: '#131B26',
      surfaceHover: '#111820',
      text: '#FFFFFF',
      text2: '#A8C0D8',
      textMuted: '#6B8FB0',
      textSubtle: '#4A6B8F',
      border: 'rgba(59, 130, 246, 0.10)',
      borderStrong: 'rgba(59, 130, 246, 0.25)',
      accent: '#3B82F6',
      accentHover: '#60A5FA',
      accentDim: 'rgba(59, 130, 246, 0.12)',
      accent2: '#06B6D4',
      red: '#F87171',
    },
    // Light Theme (Professional Edition)
    light: {
      bg: '#F1F5F9',
      surface: '#FFFFFF',
      surface2: '#E2E8F0',
      surface3: '#CBD5E1',
      surfaceHover: '#F8FAFC',
      text: '#0A0F1A',
      text2: '#1E293B',
      textMuted: '#334155',
      textSubtle: '#475569',
      border: 'rgba(59, 130, 246, 0.12)',
      borderStrong: 'rgba(59, 130, 246, 0.28)',
      accent: '#2563EB',
      accentHover: '#3B82F6',
      accentDim: 'rgba(37, 99, 235, 0.10)',
      accent2: '#0891B2',
      red: '#DC2626',
    }
  },
  typography: {
    fonts: {
      sans: 'Inter, system-ui, -apple-system, sans-serif',
      mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    },
    sizes: {
      '2xs': '10px',
      xs: '13px',
      sm: '14px',
      base: '16px',
      md: '18px',
      lg: '20px',
      xl: '25px',
      '2xl': '31px',
      '3xl': '39px',
      '4xl': '49px',
      '5xl': '61px',
      '6xl': '76px',
    },
    weights: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    }
  },
  shadows: {
    sm: '0 2px 8px rgba(0, 0, 0, 0.10)',
    lg: '0 20px 60px rgba(0, 0, 0, 0.10)',
    accent: '0 0 40px rgba(59, 130, 246, 0.30)',
  }
};

/** Hex to RGB helper for Three.js (0-1 range) */
export const hexToRgb = (hex: string): [number, number, number] => {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return [r, g, b];
};

/** Method-specific accent colors (Hex) */
export const METHOD_ACCENT_HEX = {
  'multi-perspective': '#3B82F6',
  debate:              '#E74C3C',
  jury:                '#E74C3C',
  research:            '#06B6D4',
  cove:                '#06B6D4',
  socratic:            '#7956C9',
  dialectical:         '#7956C9',
  delphi:              '#7956C9',
  scientific:          '#2063F6',
  bayesian:            '#2063F6',
  pot:                 '#2063F6',
  sot:                 '#3B82F6',
  tot:                 '#3B82F6',
  'pre-mortem':        '#F46E46',
  analogical:          '#06B6D4',
  'self-discover':     '#F4A43B',
  writing:             '#F4A43B',
} as const;

export type MethodId = keyof typeof METHOD_ACCENT_HEX;

/** RGB triples in 0-1 range for Three.js shader uniforms. */
export const METHOD_ACCENT_RGB = Object.entries(METHOD_ACCENT_HEX).reduce(
  (acc, [id, hex]) => ({ ...acc, [id]: hexToRgb(hex) }),
  {} as Record<MethodId, [number, number, number]>
);
