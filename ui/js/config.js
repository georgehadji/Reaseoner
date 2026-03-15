/**
 * ARA - Configuration
 * Method/preset mappings, phase definitions, and constants
 */

// ═══════════════════════════════════════════════════════════════════
// METHOD TO PRESETS MAPPING
// ═══════════════════════════════════════════════════════════════════

export const METHOD_PRESETS = {
  iterative: [
    { id: 'iterative-budget', label: 'Budget' },
    { id: 'iterative', label: 'Premium' }
  ],
  debate: [
    { id: 'debate-budget', label: 'Budget' },
    { id: 'debate', label: 'Premium' }
  ],
  scientific: [
    { id: 'scientific-budget', label: 'Budget' },
    { id: 'scientific-premium', label: 'Premium' }
  ],
  socratic: [
    { id: 'socratic-budget', label: 'Budget' },
    { id: 'socratic-premium', label: 'Premium' }
  ],
  'multi-perspective': [
    { id: 'basic-budget', label: 'Budget' },
    { id: 'cost-efficient', label: 'Cost-Eff' },
    { id: 'epistemic-diversity', label: 'Balanced' },
    { id: 'western-only', label: 'Western' },
    { id: 'max-quality', label: 'Premium' }
  ],
  research: [
    { id: 'research-budget', label: 'Budget' },
    { id: 'research', label: 'Premium' }
  ],
  jury: [
    { id: 'jury-budget', label: 'Budget' },
    { id: 'jury', label: 'Premium' }
  ],
  'pre-mortem': [
    { id: 'pre-mortem-budget', label: 'Budget' },
    { id: 'pre-mortem-premium', label: 'Premium' }
  ],
  bayesian: [
    { id: 'bayesian-budget', label: 'Budget' },
    { id: 'bayesian-premium', label: 'Premium' }
  ],
  dialectical: [
    { id: 'dialectical-budget', label: 'Budget' },
    { id: 'dialectical-premium', label: 'Premium' }
  ]
};

// ═══════════════════════════════════════════════════════════════════
// METHOD HINTS (Description shown in UI)
// ═══════════════════════════════════════════════════════════════════

export const METHOD_HINTS = {
  socratic: `<div class="preset-hint-title">Socratic Method</div>
<div class="preset-hint-desc">Ideal for uncovering hidden assumptions, challenging definitions, and examining if a goal is truly correct or just treating a "symptom".</div>
<div class="preset-hint-detail"><b>How it works:</b> The system plays both "Socrates" (asking tough questions) and the "Student" (answering until reaching a logical impasse).<br><b>Best input:</b> A seemingly simple, commonplace, or absolute axiom/problem that people usually accept without much thought.</div>`,

  iterative: `<div class="preset-hint-title">Iterative Method</div>
<div class="preset-hint-desc">Best for optimizing and refining an existing solution, plan, code, or prompt through continuous feedback loops.</div>
<div class="preset-hint-detail"><b>How it works:</b> The system generates an initial solution and then repeatedly critiques and refines it over multiple rounds.<br><b>Best input:</b> A draft plan, a piece of code, or a process that needs improvement or hardening.</div>`,

  debate: `<div class="preset-hint-title">Debate Method</div>
<div class="preset-hint-desc">Perfect for "A vs B" dilemmas, contested decisions, and adversarial comparison of two opposing paths.</div>
<div class="preset-hint-detail"><b>How it works:</b> Two AI personas argue for opposing sides, exchanging opening statements and rebuttals. A third AI acts as an impartial judge.<br><b>Best input:</b> A clear choice between two alternatives or a controversial strategic decision.</div>`,

  scientific: `<div class="preset-hint-title">Scientific Method</div>
<div class="preset-hint-desc">Designed for exploratory questions, formulating theories, and rigorously testing ideas against failure.</div>
<div class="preset-hint-detail"><b>How it works:</b> It generates competing, falsifiable hypotheses based on your observations, and then runs mental stress tests to try and debunk them.<br><b>Best input:</b> An unexplained observation, a drop in metrics, or a theoretical problem requiring investigation.</div>`,

  'multi-perspective': `<div class="preset-hint-title">Multi-Perspective Method</div>
<div class="preset-hint-desc">The "Swiss Army Knife" for general decisions, strategy, and complex analysis involving many variables.</div>
<div class="preset-hint-detail"><b>How it works:</b> Analyzes the problem independently from Constructive, Destructive, Systemic, and Minimalist viewpoints before synthesizing a balanced solution.<br><b>Best input:</b> "What should our strategy be?" or "Analyze the pros and cons of X."</div>`,

  research: `<div class="preset-hint-title">Research Method</div>
<div class="preset-hint-desc">For tasks requiring up-to-date facts, due diligence, and evidence-grounded claim checking.</div>
<div class="preset-hint-detail"><b>How it works:</b> Performs live web searches, vets the retrieved context for hallucinations, and grounds all claims in the gathered evidence.<br><b>Best input:</b> "What are the latest trends in X?" or "Verify the claims made in Y."</div>`,

  jury: `<div class="preset-hint-title">Jury Method</div>
<div class="preset-hint-desc">The most rigorous method for mission-critical, high-stakes decisions requiring zero regression tolerance.</div>
<div class="preset-hint-detail"><b>How it works:</b> A multi-agent system where multiple generators create solutions, multiple critics evaluate them, and verifiers check facts before a meta-judge decides.<br><b>Best input:</b> Security architecture reviews, critical financial assessments, or major irreversible product launches.</div>`,

  'pre-mortem': `<div class="preset-hint-title">Pre-Mortem Analysis</div>
<div class="preset-hint-desc">Gary Klein's prospective hindsight method — assume failure has already happened, then work backwards.</div>
<div class="preset-hint-detail"><b>How it works:</b> Projects a vivid failure scenario -> traces the root cause decision -> identifies 30-day early warning signals -> redesigns a hardened solution.<br><b>Best input:</b> Any strategic plan, product launch, investment, or decision where you want to stress-test before committing.<br><b>Based on:</b> Klein (1989) — increases risk identification by ~30%.</div>`,

  bayesian: `<div class="preset-hint-title">Bayesian Reasoning</div>
<div class="preset-hint-desc">Four-phase Bayesian epistemology — quantify uncertainty, update beliefs on evidence, test sensitivity of your assumptions.</div>
<div class="preset-hint-detail"><b>How it works:</b> Elicits prior probabilities for competing hypotheses -> assesses P(E|H) for each observation -> computes posteriors via Bayes rule -> identifies which priors most change the result if wrong.<br><b>Best input:</b> Decisions with uncertain evidence, competing explanations, or where you need to quantify confidence.<br><b>Based on:</b> Jaynes (2003) — used in clinical trials, intelligence analysis, ML model selection.</div>`,

  dialectical: `<div class="preset-hint-title">Dialectical Reasoning</div>
<div class="preset-hint-desc">Hegelian Aufhebung — move beyond thesis vs. antithesis to a qualitatively higher position that transcends both.</div>
<div class="preset-hint-detail"><b>How it works:</b> Argues the strongest affirmative thesis -> exposes internal contradictions (antithesis) -> classifies irreconcilable vs. compatible contradictions -> synthesizes a genuinely novel Aufhebung (not a compromise).<br><b>Best input:</b> Philosophical questions, strategic dilemmas with genuine tension, or any problem where "balance" is insufficient.<br><b>Based on:</b> Hegel's dialectic — thesis/antithesis/Aufhebung.</div>`
};

// ═══════════════════════════════════════════════════════════════════
// METHOD PHASES
// ═══════════════════════════════════════════════════════════════════

export const METHOD_PHASES = {
  'multi-perspective': [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Perspectives', short: 'Analyze' },
    { id: 3, name: 'Critique', short: 'Critique' },
    { id: 4, name: 'Stress Testing', short: 'Stress' },
    { id: 5, name: 'Synthesis', short: 'Synthesize' }
  ],
  iterative: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Round 1: Generate', short: 'R1-Gen' },
    { id: 3, name: 'Round 1: Critique', short: 'R1-Crit' },
    { id: 4, name: 'Round 2: Refine', short: 'R2-Ref' },
    { id: 5, name: 'Round 2: Critique', short: 'R2-Crit' },
    { id: 6, name: 'Round 3: Final', short: 'R3-Fin' },
    { id: 7, name: 'Round 3: Critique', short: 'R3-Crit' },
    { id: 8, name: 'Synthesis', short: 'Synthesize' }
  ],
  debate: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Opening', short: 'Opening' },
    { id: 3, name: 'Rebuttals', short: 'Rebuttal' },
    { id: 4, name: 'Verdict', short: 'Verdict' }
  ],
  jury: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Generation', short: 'Generate' },
    { id: 3, name: 'Critique', short: 'Critique' },
    { id: 4, name: 'Verification', short: 'Verify' },
    { id: 5, name: 'Verdict', short: 'Verdict' }
  ],
  research: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Search', short: 'Search' },
    { id: 3, name: 'Analysis', short: 'Analyze' },
    { id: 4, name: 'Verification', short: 'Verify' },
    { id: 5, name: 'Report', short: 'Report' }
  ],
  scientific: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Hypotheses', short: 'Hypothesize' },
    { id: 3, name: 'Falsification', short: 'Falsify' },
    { id: 4, name: 'Stress Testing', short: 'Stress' },
    { id: 5, name: 'Theory', short: 'Theory' }
  ],
  socratic: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Questions', short: 'Question' },
    { id: 3, name: 'Answers', short: 'Answer' },
    { id: 4, name: 'Conclusion', short: 'Conclude' }
  ],
  'pre-mortem': [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Failure Narrative', short: 'Failure' },
    { id: 3, name: 'Root Cause', short: 'Backtrack' },
    { id: 4, name: 'Early Signals', short: 'Signals' },
    { id: 5, name: 'Hardened Redesign', short: 'Redesign' },
    { id: 6, name: 'Synthesis', short: 'Synthesis' }
  ],
  bayesian: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Prior Elicitation', short: 'Priors' },
    { id: 3, name: 'Likelihood Assessment', short: 'Likelihood' },
    { id: 4, name: 'Posterior Update', short: 'Posterior' },
    { id: 5, name: 'Sensitivity Analysis', short: 'Sensitivity' },
    { id: 6, name: 'Synthesis', short: 'Synthesis' }
  ],
  dialectical: [
    { id: 0, name: 'Classification', short: 'Classify' },
    { id: 1, name: 'Decomposition', short: 'Decompose' },
    { id: 2, name: 'Thesis', short: 'Thesis' },
    { id: 3, name: 'Antithesis', short: 'Antithesis' },
    { id: 4, name: 'Contradiction Analysis', short: 'Contradict' },
    { id: 5, name: 'Aufhebung', short: 'Aufhebung' },
    { id: 6, name: 'Synthesis', short: 'Synthesis' }
  ]
};

// ═══════════════════════════════════════════════════════════════════
// METHOD CONTROLS (Which controls are visible for each method)
// ═══════════════════════════════════════════════════════════════════

export const METHOD_CONTROLS = {
  'multi-perspective': ['budget', 'expert', 'parallel'],
  iterative: ['budget', 'rounds'],
  debate: ['budget'],
  jury: ['budget', 'expert', 'verification'],
  research: ['budget', 'source_type', 'depth'],
  scientific: ['budget', 'hypotheses'],
  socratic: ['budget', 'questions'],
  'pre-mortem': ['budget'],
  bayesian: ['budget'],
  dialectical: ['budget']
};

// ═══════════════════════════════════════════════════════════════════
// METHOD METADATA
// ═══════════════════════════════════════════════════════════════════

export const METHODS = [
  {
    id: 'socratic',
    name: 'Socratic',
    icon: '❓',
    cost: 1,
    description: 'Philosophical inquiry & uncovering assumptions'
  },
  {
    id: 'scientific',
    name: 'Scientific',
    icon: '⚗',
    cost: 2,
    description: 'Technical exploration & hypothesis testing'
  },
  {
    id: 'debate',
    name: 'Debate',
    icon: '⚖',
    cost: 2,
    description: 'Contested decisions & adversarial comparison'
  },
  {
    id: 'iterative',
    name: 'Iterative',
    icon: '↻',
    cost: 3,
    description: 'Optimization of plans, code & workflows'
  },
  {
    id: 'multi-perspective',
    name: 'Multi-Perspective',
    icon: '◇',
    cost: 4,
    description: 'Strategy, trade-offs & complex analysis'
  },
  {
    id: 'research',
    name: 'Research',
    icon: '🔍',
    cost: 5,
    description: 'Fact-checking & evidence-grounded research'
  },
  {
    id: 'jury',
    name: 'Jury',
    icon: '◈',
    cost: 6,
    description: 'High-stakes decisions & technical verification'
  },
  {
    id: 'pre-mortem',
    name: 'Pre-Mortem',
    icon: '☠',
    cost: 2,
    description: 'Prospective failure analysis & resilience hardening'
  },
  {
    id: 'bayesian',
    name: 'Bayesian',
    icon: '∝',
    cost: 2,
    description: 'Quantify uncertainty, update beliefs on evidence'
  },
  {
    id: 'dialectical',
    name: 'Dialectical',
    icon: '⟳',
    cost: 2,
    description: 'Hegelian Aufhebung — thesis → antithesis → transcendence'
  }
];

// ═══════════════════════════════════════════════════════════════════
// API ENDPOINTS
// ═══════════════════════════════════════════════════════════════════

export const API = {
  RUN: '/api/run',
  STOP: '/api/stop',
  CACHE: '/api/cache',
  PRESETS: '/api/presets',
  MODELS: '/api/models'
};

// ═══════════════════════════════════════════════════════════════════
// DEFAULT VALUES
// ═══════════════════════════════════════════════════════════════════

export const DEFAULTS = {
  method: 'multi-perspective',
  topK: 2,
  maxRounds: 3,
  maxHypotheses: 3,
  maxQuestions: 4
};