'use client';

import { RenderedPhase } from '@/components/chat/ChatFeed';
import { TypewriterMarkdown } from '@/components/chat/TypewriterMarkdown';
import { PhaseCard } from './PhaseCard';
import { SynthesisCard } from './SynthesisCard';
import { ClassificationCard } from './ClassificationCard';
import { CritiqueCard } from './CritiqueCard';
import { buildMarkdownFromPhase } from '@/lib/markdown';

function isSynthesisPhase(name: string): boolean {
  return /synthesis|report|theory|conclusion|verdict|redesign|aufhebung|transfer/i.test(name);
}

interface PhaseRendererProps {
  phase: RenderedPhase;
}

function getTokens(data: unknown): { input?: number; output?: number } | null {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  const t = d.tokens;
  if (!t || typeof t !== 'object') return null;
  const tokens = t as Record<string, unknown>;
  const input = typeof tokens.input === 'number' ? tokens.input : undefined;
  const output = typeof tokens.output === 'number' ? tokens.output : undefined;
  if (input == null && output == null) return null;
  return { input, output };
}

function getModels(data: unknown): string[] | null {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  const m = d.models;
  if (!Array.isArray(m)) return null;
  return m.filter((x): x is string => typeof x === 'string');
}

function getSubagents(data: unknown): Array<{ name: string; model: string; tokens_in?: number; tokens_out?: number; duration_ms?: number; error?: string | null }> | null {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  const s = d.subagents;
  if (!Array.isArray(s)) return null;
  return s.filter((x): x is Record<string, unknown> => typeof x === 'object' && x !== null).map((x) => ({
    name: String(x.name || 'unknown'),
    model: String(x.model || 'unknown'),
    tokens_in: typeof x.tokens_in === 'number' ? x.tokens_in : undefined,
    tokens_out: typeof x.tokens_out === 'number' ? x.tokens_out : undefined,
    duration_ms: typeof x.duration_ms === 'number' ? x.duration_ms : undefined,
    error: x.error != null ? String(x.error) : undefined,
  }));
}

function getDuration(data: unknown): number | undefined {
  if (!data || typeof data !== 'object') return undefined;
  const d = data as Record<string, unknown>;
  const duration = d.duration;
  return typeof duration === 'number' ? duration : undefined;
}

export function PhaseRenderer({ phase }: PhaseRendererProps) {
  const { index, phase: phaseNum, name, data } = phase;
  const tokens = getTokens(data);
  const models = getModels(data);
  const subagents = getSubagents(data);
  const duration = getDuration(data);

  // Direct Response / Web Search: render inline without a phase card
  if (name === 'Direct Response' || name === 'Web Search') {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <TypewriterMarkdown text={md} wordsPerSecond={10} />
    );
  }

  // Classification
  if (
    phaseNum === 0 &&
    data &&
    typeof data === 'object' &&
    ('task_type' in data || 'rationale' in data)
  ) {
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration}>
        <ClassificationCard data={data} />
      </PhaseCard>
    );
  }

  // Critique (only if there are actual scores)
  const scoresArray = (data as Record<string, unknown>).scores;
  if (
    phaseNum === 3 &&
    data &&
    typeof data === 'object' &&
    Array.isArray(scoresArray) &&
    scoresArray.length > 0
  ) {
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration}>
        <CritiqueCard data={data} />
      </PhaseCard>
    );
  }

  // Scientific state (hypotheses + falsification tests)
  const scientificState = (data as Record<string, unknown>).scientific_state as Record<string, unknown> | undefined;
  if (
    scientificState &&
    (Array.isArray(scientificState.hypotheses) || Array.isArray(scientificState.test_results))
  ) {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration}>
        <TypewriterMarkdown text={md} wordsPerSecond={10} />
      </PhaseCard>
    );
  }

  // Socratic state (questions + answers)
  const socraticState = (data as Record<string, unknown>).socratic_state as Record<string, unknown> | undefined;
  if (
    socraticState &&
    (Array.isArray(socraticState.questions) || Array.isArray(socraticState.answers))
  ) {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration}>
        <TypewriterMarkdown text={md} wordsPerSecond={10} />
      </PhaseCard>
    );
  }

  // Synthesis
  if (
    isSynthesisPhase(name) &&
    data &&
    typeof data === 'object' &&
    ('core_solution' in data || 'action_blueprint' in data)
  ) {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <SynthesisCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration}>
        <TypewriterMarkdown text={md} wordsPerSecond={10} />
      </SynthesisCard>
    );
  }

  // Fallback to markdown for everything else
  const md = buildMarkdownFromPhase(index, phaseNum, name, data);
  return (
    <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration}>
      <TypewriterMarkdown text={md} wordsPerSecond={10} />
    </PhaseCard>
  );
}
