import { MethodPhase } from './types';

// Phase timeline labels per method — still used by PhaseTimeline component.
// Keyed by the method name that the backend echoes in the SSE start event
// as `auto_selected_method` (snake_case) or derived from the effective preset.
export const METHOD_PHASES: Record<string, MethodPhase[]> = {
  'multi-perspective': [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Perspectives', short: 'Analyze' },
    { id: 3, name: 'Critique', short: 'Critique' },
    { id: 4, name: 'Stress Testing', short: 'Stress' },
    { id: 5, name: 'Synthesis', short: 'Synthesize' },
  ],
  debate: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Opening', short: 'Opening' },
    { id: 3, name: 'Rebuttals', short: 'Rebuttal' },
    { id: 4, name: 'Verdict', short: 'Verdict' },
    { id: 5, name: 'Synthesis', short: 'Synthesize' },
  ],
  jury: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Generation', short: 'Generate' },
    { id: 3, name: 'Critique', short: 'Critique' },
    { id: 4, name: 'Verification', short: 'Verify' },
    { id: 5, name: 'Verdict', short: 'Verdict' },
  ],
  research: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Search', short: 'Search' },
    { id: 3, name: 'Analysis', short: 'Analyze' },
    { id: 4, name: 'Verification', short: 'Verify' },
    { id: 5, name: 'Report', short: 'Report' },
  ],
  scientific: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Hypotheses', short: 'Hypothesize' },
    { id: 3, name: 'Falsification', short: 'Falsify' },
    { id: 4, name: 'Stress Testing', short: 'Stress' },
    { id: 5, name: 'Theory', short: 'Theory' },
  ],
  socratic: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Questions', short: 'Question' },
    { id: 3, name: 'Answers', short: 'Answer' },
    { id: 4, name: 'Conclusion', short: 'Conclude' },
  ],
  'pre-mortem': [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Failure Modes', short: 'Failures' },
    { id: 3, name: 'Backtrack', short: 'Backtrack' },
    { id: 4, name: 'Signals', short: 'Signals' },
    { id: 5, name: 'Redesign', short: 'Redesign' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
  bayesian: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Priors', short: 'Priors' },
    { id: 3, name: 'Likelihood', short: 'Likelihood' },
    { id: 4, name: 'Posterior', short: 'Posterior' },
    { id: 5, name: 'Sensitivity', short: 'Sensitivity' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
  dialectical: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Thesis', short: 'Thesis' },
    { id: 3, name: 'Antithesis', short: 'Antithesis' },
    { id: 4, name: 'Contradictions', short: 'Contradict' },
    { id: 5, name: 'Aufhebung', short: 'Aufhebung' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
  analogical: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Abstraction', short: 'Abstract' },
    { id: 3, name: 'Domain Search', short: 'Search' },
    { id: 4, name: 'Mapping', short: 'Map' },
    { id: 5, name: 'Transfer', short: 'Transfer' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
  delphi: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Round 1', short: 'R1' },
    { id: 3, name: 'Aggregation', short: 'Aggregate' },
    { id: 4, name: 'Round 2', short: 'R2' },
    { id: 5, name: 'Convergence', short: 'Converge' },
    { id: 6, name: 'Dissent', short: 'Dissent' },
    { id: 7, name: 'Synthesis', short: 'Synthesize' },
  ],
  cove: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Draft', short: 'Draft' },
    { id: 3, name: 'Verify', short: 'Verify' },
    { id: 4, name: 'Answer', short: 'Answer' },
    { id: 5, name: 'Revise', short: 'Revise' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
  sot: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Skeleton', short: 'Skeleton' },
    { id: 3, name: 'Parallel Solve', short: 'Solve' },
    { id: 4, name: 'Assemble', short: 'Assemble' },
    { id: 5, name: 'Synthesis', short: 'Synthesize' },
  ],
  tot: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Decompose', short: 'Decompose' },
    { id: 3, name: 'Generate', short: 'Generate' },
    { id: 4, name: 'Evaluate', short: 'Evaluate' },
    { id: 5, name: 'Select', short: 'Select' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
  pot: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Code Gen', short: 'Code' },
    { id: 3, name: 'Execute', short: 'Execute' },
    { id: 4, name: 'Interpret', short: 'Interpret' },
    { id: 5, name: 'Synthesis', short: 'Synthesize' },
  ],
  'self-discover': [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 1.5, name: 'Deep Read', short: 'Read' },
    { id: 2, name: 'Select Modules', short: 'Select' },
    { id: 3, name: 'Adapt', short: 'Adapt' },
    { id: 4, name: 'Execute', short: 'Execute' },
    { id: 5, name: 'Reflect', short: 'Reflect' },
    { id: 6, name: 'Synthesis', short: 'Synthesize' },
  ],
};

/** Example prompts shown in the centered empty-state composer. */
export const EXAMPLE_PROMPTS: string[] = [
  'Should I bootstrap or raise VC?',
  'What assumptions am I making about remote work?',
  'Should companies ban internal email?',
  'Why did our product launch fail?',
  'Can caffeine improve long-term memory?',
  'What does the evidence say about 4-day work weeks?',
  'How is building a startup like playing poker?',
  'Free will vs determinism — what survives scrutiny?',
  'What will the price of lithium be in 2030?',
];

export const API = {
  RUN: '/api/run',
  STOP: '/api/stop',
  CACHE: '/api/cache',
  PRESETS: '/api/presets',
  MODELS: '/api/models',
};

export const DEFAULTS = {
  tier: 'budget' as 'budget' | 'premium',
  topK: 2,
  typewriterWordsPerSecond: 20,
};

/** Typography sizes per DESIGN.md hierarchy. */
export const TEXT_SIZES = {
  /** DESIGN.md Tiny (10px) — badges, fine print, source numbers. */
  tiny: 'text-[10px]',
  /** Synthesis / final output — maps to DESIGN.md Body (~18px). */
  synthesis: 'text-[17px] leading-relaxed',
  /** Intermediate phase cards — maps to DESIGN.md Nav/UI (15px). */
  phaseCard: 'text-[15px] leading-relaxed',
  /** Chat feed body — maps to DESIGN.md Body (18px). */
  body: 'text-[18px]',
};

export const TIMING = {
  copiedFeedbackMs: 2000,
  streamingBounceDelays: [0, 150, 300] as const,
  serverStatusAbortTimeoutMs: 5000,
  serverStatusCheckIntervalMs: 10000,
  presetsRefreshIntervalMs: 60000,
  scrollAnchorThresholdPx: 120,
  durationFormatMsThreshold: 1000,
};
