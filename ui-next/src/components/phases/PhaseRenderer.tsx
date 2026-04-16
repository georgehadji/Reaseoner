'use client';

import { RenderedPhase } from '@/components/chat/ChatFeed';
import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer';
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

export function PhaseRenderer({ phase }: PhaseRendererProps) {
  const { index, phase: phaseNum, name, data } = phase;
  const tokens = getTokens(data);
  const models = getModels(data);

  // Classification
  if (
    phaseNum === 0 &&
    data &&
    typeof data === 'object' &&
    ('task_type' in data || 'rationale' in data)
  ) {
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models}>
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
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models}>
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
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models}>
        <div className="markdown-body text-[17px] leading-relaxed">
          <MarkdownRenderer>{md}</MarkdownRenderer>
        </div>
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
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models}>
        <div className="markdown-body text-[17px] leading-relaxed">
          <MarkdownRenderer>{md}</MarkdownRenderer>
        </div>
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
      <SynthesisCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models}>
        <div className="markdown-body text-[17px] leading-relaxed">
          <MarkdownRenderer>{md}</MarkdownRenderer>
        </div>
      </SynthesisCard>
    );
  }

  // Fallback to markdown for everything else
  const md = buildMarkdownFromPhase(index, phaseNum, name, data);
  return (
    <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models}>
      <div className="markdown-body text-[17px] leading-relaxed">
        <MarkdownRenderer>{md}</MarkdownRenderer>
      </div>
    </PhaseCard>
  );
}
