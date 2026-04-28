/**
 * Accent colors per reasoning method — passed to NebulaBackground shader.
 * Colors are in RGB 0-1 range for Three.js uniforms.
 */

export type MethodId =
  | 'socratic'
  | 'debate'
  | 'scientific'
  | 'multi-perspective'
  | 'research'
  | 'jury'
  | 'pre-mortem'
  | 'bayesian'
  | 'dialectical'
  | 'analogical'
  | 'delphi'
  | 'cove'
  | 'sot'
  | 'tot'
  | 'pot'
  | 'self-discover'
  | 'writing';

/** RGB triples in 0-1 range for Three.js shader uniforms. */
export const METHOD_ACCENT_RGB: Record<MethodId, [number, number, number]> = {
  // Default / balanced
  'multi-perspective': [0.0, 0.788, 0.694],   // Teal #00C9B1

  // Adversarial / conflict
  debate:              [0.906, 0.298, 0.235],  // Red #E74C3C
  jury:                [0.945, 0.769, 0.059],  // Gold #F1C40F

  // Research / evidence
  research:            [0.180, 0.800, 0.443],  // Green #2ECC71
  cove:                [0.365, 0.678, 0.886],  // Sky blue #5DADE2

  // Philosophy / wisdom
  socratic:            [0.608, 0.349, 0.714],  // Purple #9B59B6
  dialectical:         [0.557, 0.267, 0.678],  // Deep purple #8E44AD
  delphi:              [0.831, 0.675, 0.051],  // Dark gold #D4AC0D

  // Science / math
  scientific:          [0.204, 0.596, 0.859],  // Blue #3498DB
  bayesian:            [0.106, 0.737, 0.612],  // Turquoise #1ABC9C
  pot:                 [0.153, 0.682, 0.376],  // Forest green #27AE60

  // Structure / planning
  sot:                 [0.647, 0.412, 0.741],  // Light purple #A569BD
  tot:                 [0.180, 0.525, 0.757],  // Steel blue #2E86C1

  // Risk / warning
  'pre-mortem':        [0.902, 0.494, 0.133],  // Orange #E67E22

  // Nature / cross-domain
  analogical:          [0.086, 0.627, 0.522],  // Green-teal #16A085

  // Dynamic / adaptive
  'self-discover':     [0.906, 0.298, 0.235],  // Red #E74C3C

  // Creative / writing
  writing:             [0.961, 0.620, 0.043],  // Amber #F59E0B
};

/** Hex values for CSS / UI usage. */
export const METHOD_ACCENT_HEX: Record<MethodId, string> = {
  'multi-perspective': '#00C9B1',
  debate:              '#E74C3C',
  jury:                '#F1C40F',
  research:            '#2ECC71',
  cove:                '#5DADE2',
  socratic:            '#9B59B6',
  dialectical:         '#8E44AD',
  delphi:              '#D4AC0D',
  scientific:          '#3498DB',
  bayesian:            '#1ABC9C',
  pot:                 '#27AE60',
  sot:                 '#A569BD',
  tot:                 '#2E86C1',
  'pre-mortem':        '#E67E22',
  analogical:          '#16A085',
  'self-discover':     '#E74C3C',
  writing:             '#F59E0B',
};

/** Default fallback when no method is active. */
export const DEFAULT_ACCENT_RGB: [number, number, number] = METHOD_ACCENT_RGB['multi-perspective'];
