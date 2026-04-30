/* eslint-disable react/no-unescaped-entities */
import { MethodId } from './types';

export interface MethodHintData {
  title: string;
  desc: string;
  detail: React.ReactNode;
}

export const METHOD_HINTS_DATA: Record<MethodId, MethodHintData> = {
  socratic: {
    title: 'Socratic Method',
    desc: 'Ideal for uncovering hidden assumptions, challenging definitions, and examining if a goal is truly correct or just treating a "symptom".',
    detail: (
      <>
        <b>How it works:</b> The system plays both "Socrates" (asking tough questions) and the "Student" (answering until reaching a logical impasse).
        <br />
        <b>Best input:</b> A seemingly simple, commonplace, or absolute axiom/problem that people usually accept without much thought.
      </>
    ),
  },
  debate: {
    title: 'Debate Method',
    desc: 'Perfect for "A vs B" dilemmas, contested decisions, and adversarial comparison of two opposing paths.',
    detail: (
      <>
        <b>How it works:</b> Two AI personas argue for opposing sides, exchanging opening statements and rebuttals. A third AI acts as an impartial judge.
        <br />
        <b>Best input:</b> A clear choice between two alternatives or a controversial strategic decision.
      </>
    ),
  },
  scientific: {
    title: 'Scientific Method',
    desc: 'Designed for exploratory questions, formulating theories, and rigorously testing ideas against failure.',
    detail: (
      <>
        <b>How it works:</b> It generates competing, falsifiable hypotheses based on your observations, and then runs mental stress tests to try and debunk them.
        <br />
        <b>Best input:</b> An unexplained observation, a drop in metrics, or a theoretical problem requiring investigation.
      </>
    ),
  },
  'multi-perspective': {
    title: 'Multi-Perspective Method',
    desc: 'The "Swiss Army Knife" for general decisions, strategy, and complex analysis involving many variables.',
    detail: (
      <>
        <b>How it works:</b> Analyzes the problem independently from Constructive, Destructive, Systemic, and Minimalist viewpoints before synthesizing a balanced solution.
        <br />
        <b>Best input:</b> "What should our strategy be?" or "Analyze the pros and cons of X."
      </>
    ),
  },
  research: {
    title: 'Research Method',
    desc: 'For tasks requiring up-to-date facts, due diligence, and evidence-grounded claim checking.',
    detail: (
      <>
        <b>How it works:</b> Performs live web searches, vets the retrieved context for hallucinations, and grounds all claims in the gathered evidence.
        <br />
        <b>Best input:</b> "What are the latest trends in X?" or "Verify the claims made in Y."
      </>
    ),
  },
  jury: {
    title: 'Jury Method',
    desc: 'The most rigorous method for mission-critical, high-stakes decisions requiring zero regression tolerance.',
    detail: (
      <>
        <b>How it works:</b> A multi-agent system where multiple generators create solutions, multiple critics evaluate them, and verifiers check facts before a meta-judge decides.
        <br />
        <b>Best input:</b> Security architecture reviews, critical financial assessments, or major irreversible product launches.
      </>
    ),
  },
  'pre-mortem': {
    title: 'Pre-Mortem Analysis',
    desc: "Gary Klein's prospective hindsight method — assume failure has already happened, then work backwards.",
    detail: (
      <>
        <b>How it works:</b> Projects a vivid failure scenario -&gt; traces the root cause decision -&gt; identifies 30-day early warning signals -&gt; redesigns a hardened solution.
        <br />
        <b>Best input:</b> Any strategic plan, product launch, investment, or decision where you want to stress-test before committing.
        <br />
        <b>Based on:</b> Klein (1989) — increases risk identification by ~30%.
      </>
    ),
  },
  bayesian: {
    title: 'Bayesian Reasoning',
    desc: 'Four-phase Bayesian epistemology — quantify uncertainty, update beliefs on evidence, test sensitivity of your assumptions.',
    detail: (
      <>
        <b>How it works:</b> Elicits prior probabilities for competing hypotheses -&gt; assesses P(E|H) for each observation -&gt; computes posteriors via Bayes rule -&gt; identifies which priors most change the result if wrong.
        <br />
        <b>Best input:</b> Decisions with uncertain evidence, competing explanations, or where you need to quantify confidence.
        <br />
        <b>Based on:</b> Jaynes (2003) — used in clinical trials, intelligence analysis, ML model selection.
      </>
    ),
  },
  dialectical: {
    title: 'Dialectical Reasoning',
    desc: 'Hegelian Aufhebung — move beyond thesis vs. antithesis to a qualitatively higher position that transcends both.',
    detail: (
      <>
        <b>How it works:</b> Argues the strongest affirmative thesis -&gt; exposes internal contradictions (antithesis) -&gt; classifies irreconcilable vs. compatible contradictions -&gt; synthesizes a genuinely novel Aufhebung (not a compromise).
        <br />
        <b>Best input:</b> Philosophical questions, strategic dilemmas with genuine tension, or any problem where "balance" is insufficient.
        <br />
        <b>Based on:</b> Hegel's dialectic — thesis/antithesis/Aufhebung.
      </>
    ),
  },
  analogical: {
    title: 'Analogical Reasoning',
    desc: 'Structure-mapping theory — find isomorphic problems solved in other domains, then transfer the solution.',
    detail: (
      <>
        <b>How it works:</b> Abstracts the deep structure of your problem -&gt; searches for isomorphic solutions in other fields (biomimicry, history, engineering, biology, economics) -&gt; maps elements structurally -&gt; transfers the solution and identifies where the analogy breaks.
        <br />
        <b>Best input:</b> Novel problems that seem unsolvable in their domain but may have known solutions elsewhere.
        <br />
        <b>Based on:</b> Gentner (1983) Structure-Mapping Theory, TRIZ, biomimicry.
      </>
    ),
  },
  delphi: {
    title: 'Delphi Method',
    desc: 'RAND Delphi expert consensus — 4 independent experts, anonymous aggregation, convergence tracking, and mandatory minority dissent.',
    detail: (
      <>
        <b>How it works:</b> 4 experts independently estimate → anonymous median + IQR computed → experts revise or defend with full anonymity → convergence checked → outlier expert documents dissenting rationale.
        <br />
        <b>Best input:</b> Forecasting questions, policy decisions, or any problem where expert consensus and minority viewpoints both matter.
        <br />
        <b>Based on:</b> Dalkey & Helmer (1963) — used in IPCC climate reports, WHO policy, military forecasting.
      </>
    ),
  },
  cove: {
    title: 'Chain-of-Verification (CoVe)',
    desc: 'Structured fact-checking pipeline: draft claims, verify each against evidence, answer with corrections, and revise.',
    detail: (
      <>
        <b>How it works:</b> Generates a baseline response → extracts atomic claims → verifies each claim via independent search/LLM calls → produces a corrected, fact-grounded answer.
        <br />
        <b>Best input:</b> Any response where factual accuracy matters more than speed — research reports, technical documentation, data analysis.
      </>
    ),
  },
  sot: {
    title: 'Skeleton-of-Thought (SoT)',
    desc: 'Parallel composition: generate a structural outline first, then fill each section concurrently.',
    detail: (
      <>
        <b>How it works:</b> Produces a high-level bullet skeleton of the answer → dispatches each skeleton point to an independent parallel generation → assembles the filled sections into a coherent response.
        <br />
        <b>Best input:</b> Multi-part questions, complex explanations that benefit from structured parallel composition rather than linear generation.
      </>
    ),
  },
  tot: {
    title: 'Tree-of-Thought (ToT)',
    desc: 'Explore multiple reasoning branches with evaluation-guided backtracking and selection.',
    detail: (
      <>
        <b>How it works:</b> Decomposes the problem into decision steps → at each step, generates multiple candidate "thoughts" → evaluates each with a heuristic → backtracks from dead ends → selects the highest-scoring path.
        <br />
        <b>Best input:</b> Planning problems, puzzles, math proofs, or any task requiring strategic exploration with backtracking.
      </>
    ),
  },
  pot: {
    title: 'Program-of-Thought (PoT)',
    desc: 'Use executable code as intermediate reasoning steps for precise numerical and logical computation.',
    detail: (
      <>
        <b>How it works:</b> Generates Python code that models the problem → executes it in a sandboxed environment → interprets the output to produce a natural language answer with verified numerical results.
        <br />
        <b>Best input:</b> Numerical analysis, data transformation, statistical reasoning, or any problem requiring precise computation rather than heuristic estimation.
      </>
    ),
  },
  'self-discover': {
    title: 'Self-Discover',
    desc: 'Dynamically compose reasoning modules (e.g., break down, critical thinking, step-by-step) to fit the specific problem.',
    detail: (
      <>
        <b>How it works:</b> Selects relevant atomic reasoning modules from a predefined set → adapts them to the problem context → executes them in a structured sequence determined by the problem structure rather than a fixed pipeline.
        <br />
        <b>Best input:</b> Ill-structured problems that don't fit neatly into a single reasoning paradigm — creative strategy, novel analysis, interdisciplinary questions.
      </>
    ),
  },
  writing: {
    title: 'Article / Essay Writing',
    desc: 'Research-backed article generation with structured outline, evidence gathering, drafting, and fact-checking.',
    detail: (
      <>
        <b>How it works:</b> Decomposes the topic into sections → gathers evidence via web search → drafts each section with citations → verifies claims against sources → revises for coherence and flow.
        <br />
        <b>Best input:</b> In-depth articles, research reports, blog posts, or any long-form content requiring factual grounding and structured argumentation.
      </>
    ),
  },
  brainstorming: {
    title: 'Brainstorming',
    desc: 'Generate, cluster, and refine creative ideas using structured divergent and convergent thinking.',
    detail: (
      <>
        <b>How it works:</b> Generates a large quantity of diverse ideas → clusters them by theme → evaluates each for novelty, feasibility, and impact → refines the most promising into actionable concepts.
        <br />
        <b>Best input:</b> Creative challenges, product feature ideation, marketing angles, or any problem where you need fresh perspectives.
      </>
    ),
  },
};
