'use client';

import { useRef, useEffect, memo } from 'react';
import { RenderedPhase } from '@/components/chat/ChatFeed';
import { DEFAULTS } from '@/lib/config';
import { TypewriterMarkdown } from '@/components/chat/TypewriterMarkdown';
import { MarkdownRenderer } from '@/components/chat/MarkdownRenderer';
import { PhaseCard } from './PhaseCard';
import { SynthesisCard } from './SynthesisCard';
import { ClassificationCard } from './ClassificationCard';
import { CritiqueCard } from './CritiqueCard';
import { buildMarkdownFromPhase } from '@/lib/markdown';
import { copyToClipboard } from '@/lib/utils';
import { isEnabled } from '@/hooks/useFeatureFlags';

function isSynthesisPhase(name: string): boolean {
  return /synthesis|report|theory|conclusion|verdict|redesign|aufhebung|transfer/i.test(name);
}

interface PhaseRendererProps {
  phase: RenderedPhase;
  onComplete?: () => void;
  animationKey?: string;
  animated?: boolean;
  forceOpen?: boolean | null;
  errorPhases?: number[];
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

function getSynthesisSections(data: unknown): {
  criticalInsights: string[];
  actionBlueprint: Array<string | { step?: string; action?: string }>;
  openQuestions: string[];
  sources: Array<{ title?: string; url?: string }>;
} | null {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  return {
    criticalInsights: Array.isArray(d.critical_insights) ? (d.critical_insights as string[]) : [],
    actionBlueprint: Array.isArray(d.action_blueprint) ? (d.action_blueprint as Array<string | { step?: string; action?: string }>) : [],
    openQuestions: Array.isArray(d.open_questions) ? (d.open_questions as string[]) : [],
    sources: Array.isArray(d.sources) ? (d.sources as Array<{ title?: string; url?: string }>) : [],
  };
}

function getSynthesisHighlights(data: unknown): Array<{ label: string; value: number }> | null {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;
  const highlights = [
    { label: 'insights', value: Array.isArray(d.critical_insights) ? d.critical_insights.length : 0 },
    { label: 'actions', value: Array.isArray(d.action_blueprint) ? d.action_blueprint.length : 0 },
    { label: 'questions', value: Array.isArray(d.open_questions) ? d.open_questions.length : 0 },
    { label: 'sources', value: Array.isArray(d.sources) ? d.sources.length : 0 },
  ].filter((item) => item.value > 0);
  return highlights.length > 0 ? highlights : null;
}

function getVettedContext(data: unknown): Array<Record<string, unknown>> {
  if (!data || typeof data !== 'object') return [];
  const d = data as Record<string, unknown>;
  const context = d.vetted_context;
  if (!Array.isArray(context)) return [];
  return context.filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null);
}

export const PhaseRenderer = memo(function PhaseRenderer({ phase, onComplete, animationKey, animated = true, forceOpen = null, errorPhases = [] }: PhaseRendererProps) {
  const { index, phase: phaseNum, name, data } = phase;
  const tokens = getTokens(data);
  const models = getModels(data);
  const subagents = getSubagents(data);
  const duration = getDuration(data);
  const synthesisHighlights = getSynthesisHighlights(data);
  const synthesisSections = getSynthesisSections(data);
  const vettedContext = getVettedContext(data);
  const isCompact = isEnabled('compact-phases') && !isSynthesisPhase(name) && phaseNum !== 0;
  const defaultOpen = isSynthesisPhase(name) || phaseNum === 0;

  // Direct Response / Web Search: render inline without a phase card
  if (name === 'Direct Response' || name === 'Web Search') {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return animated ? (
      <TypewriterMarkdown text={md} wordsPerSecond={DEFAULTS.typewriterWordsPerSecond} onComplete={onComplete} animationKey={animationKey} />
    ) : (
      <MarkdownRenderer>{md}</MarkdownRenderer>
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
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} defaultOpen={defaultOpen} forceOpen={forceOpen} compact={isCompact} status={errorPhases.includes(phaseNum) ? 'error' : 'completed'}>
        <ClassificationCard data={data} />
        {onComplete && <CompletionTrigger onComplete={onComplete} />}
      </PhaseCard>
    );
  }

  // Critique (only if there are actual scores)
  const scoresArray = data && typeof data === 'object' ? (data as Record<string, unknown>).scores : undefined;
  if (
    phaseNum === 3 &&
    data &&
    typeof data === 'object' &&
    Array.isArray(scoresArray) &&
    scoresArray.length > 0
  ) {
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} defaultOpen={defaultOpen} forceOpen={forceOpen} compact={isCompact} status={errorPhases.includes(phaseNum) ? 'error' : 'completed'}>
        <CritiqueCard data={data} />
        {onComplete && <CompletionTrigger onComplete={onComplete} />}
      </PhaseCard>
    );
  }

  // Scientific state (hypotheses + falsification tests)
  const scientificState = data && typeof data === 'object' ? (data as Record<string, unknown>).scientific_state as Record<string, unknown> | undefined : undefined;
  if (
    scientificState &&
    (Array.isArray(scientificState.hypotheses) || Array.isArray(scientificState.test_results))
  ) {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} defaultOpen={defaultOpen} forceOpen={forceOpen} compact={isCompact} status={errorPhases.includes(phaseNum) ? 'error' : 'completed'}>
        {vettedContext.length > 0 && <VettedContextBlock items={vettedContext} />}
        {animated ? (
          <TypewriterMarkdown text={md} wordsPerSecond={DEFAULTS.typewriterWordsPerSecond} onComplete={onComplete} animationKey={animationKey} />
        ) : (
          <MarkdownRenderer>{md}</MarkdownRenderer>
        )}
      </PhaseCard>
    );
  }

  // Socratic state (questions + answers)
  const socraticState = data && typeof data === 'object' ? (data as Record<string, unknown>).socratic_state as Record<string, unknown> | undefined : undefined;
  if (
    socraticState &&
    (Array.isArray(socraticState.questions) || Array.isArray(socraticState.answers))
  ) {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} defaultOpen={defaultOpen} forceOpen={forceOpen} compact={isCompact} status={errorPhases.includes(phaseNum) ? 'error' : 'completed'}>
        {vettedContext.length > 0 && <VettedContextBlock items={vettedContext} />}
        {animated ? (
          <TypewriterMarkdown text={md} wordsPerSecond={DEFAULTS.typewriterWordsPerSecond} onComplete={onComplete} animationKey={animationKey} />
        ) : (
          <MarkdownRenderer>{md}</MarkdownRenderer>
        )}
      </PhaseCard>
    );
  }

  // Writing state (outline, draft, fact-check, final article)
  const writingState = data && typeof data === 'object' ? (data as Record<string, unknown>).writing_state as Record<string, unknown> | undefined : undefined;
  if (
    writingState &&
    (Array.isArray(writingState.outline) ||
     typeof writingState.article === 'string' ||
     Array.isArray(writingState.factcheck_reviews) ||
     typeof writingState.final_article === 'string')
  ) {
    const md = buildMarkdownFromPhase(index, phaseNum, name, data);
    return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} defaultOpen={defaultOpen} forceOpen={forceOpen} compact={isCompact} status={errorPhases.includes(phaseNum) ? 'error' : 'completed'}>
        {vettedContext.length > 0 && <VettedContextBlock items={vettedContext} />}
        {animated ? (
          <TypewriterMarkdown text={md} wordsPerSecond={DEFAULTS.typewriterWordsPerSecond} onComplete={onComplete} animationKey={animationKey} />
        ) : (
          <MarkdownRenderer>{md}</MarkdownRenderer>
        )}
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
    const md = buildMarkdownFromPhase(index, phaseNum, name, data, {
      omitSections: ['critical_insights', 'action_blueprint', 'open_questions', 'sources'],
    });
    return (
      <SynthesisCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} highlights={synthesisHighlights} sources={synthesisSections?.sources} defaultOpen>
        {synthesisSections && (
          <div className="mb-4 grid gap-4">
            {synthesisSections.criticalInsights.length > 0 && (
              <section id="critical-insights" className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <h3 className="mb-2 text-sm font-semibold text-[var(--text)]">Critical Insights</h3>
                <ol className="list-decimal space-y-1 pl-5 text-[15px] text-[var(--text)]">
                  {synthesisSections.criticalInsights.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ol>
              </section>
            )}
            {synthesisSections.actionBlueprint.length > 0 && (
              <section id="action-blueprint" className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h3 className="text-sm font-semibold text-[var(--text)]">Action Blueprint</h3>
                  <button
                    type="button"
                    onClick={() => {
                      const lines = synthesisSections.actionBlueprint.map((item, i) => {
                        if (typeof item === 'string') return `- ${item}`;
                        const step = item.step || `Step ${i + 1}`;
                        const action = item.action || '';
                        return `- ${step}: ${action}`;
                      });
                      copyToClipboard(lines.join('\n'));
                    }}
                    className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1 text-[10px] font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]"
                  >
                    Copy actions
                  </button>
                </div>
                <ul className="space-y-1 text-[15px] text-[var(--text)]">
                  {synthesisSections.actionBlueprint.map((item, i) => {
                    if (typeof item === 'string') {
                      return <li key={i}>• {item}</li>;
                    }
                    const step = item.step || `Step ${i + 1}`;
                    const action = item.action || '';
                    return (
                      <li key={i}>
                        <span className="font-semibold">{step}:</span> {action}
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}
            {synthesisSections.openQuestions.length > 0 && (
              <section id="open-questions" className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <h3 className="mb-2 text-sm font-semibold text-[var(--text)]">Open Questions</h3>
                <ul className="space-y-1 text-[15px] text-[var(--text)]">
                  {synthesisSections.openQuestions.map((item, i) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              </section>
            )}
            {synthesisSections.sources.length > 0 && (
              <section id="sources" className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
                <h3 className="mb-2 text-sm font-semibold text-[var(--text)]">Sources</h3>
                <ul className="space-y-1 text-[15px] text-[var(--text)]">
                  {synthesisSections.sources.map((source, i) => (
                    <li key={i}>
                      {source.url ? (
                        <a href={source.url} target="_blank" rel="noopener noreferrer" className="underline">
                          {source.title || source.url}
                        </a>
                      ) : (
                        source.title || 'Source'
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}
        {animated ? (
          <TypewriterMarkdown text={md} wordsPerSecond={DEFAULTS.typewriterWordsPerSecond} onComplete={onComplete} animationKey={animationKey} />
        ) : (
          <MarkdownRenderer>{md}</MarkdownRenderer>
        )}
      </SynthesisCard>
    );
  }

  // Fallback to markdown for everything else
  const md = buildMarkdownFromPhase(index, phaseNum, name, data, {
    omitSections: isSynthesisPhase(name) ? ['critical_insights', 'action_blueprint', 'open_questions', 'sources'] : undefined,
  });
  return (
      <PhaseCard index={index} phase={phaseNum} name={name} tokens={tokens} models={models} subagents={subagents} duration={duration} defaultOpen={defaultOpen} forceOpen={forceOpen} compact={isCompact} status={errorPhases.includes(phaseNum) ? 'error' : 'completed'}>
      {vettedContext.length > 0 && <VettedContextBlock items={vettedContext} />}
      {animated ? (
        <TypewriterMarkdown text={md} wordsPerSecond={DEFAULTS.typewriterWordsPerSecond} onComplete={onComplete} animationKey={animationKey} />
      ) : (
        <MarkdownRenderer>{md}</MarkdownRenderer>
      )}
    </PhaseCard>
  );
});

function VettedContextBlock({ items }: { items: Array<Record<string, unknown>> }) {
  return (
    <div className="mb-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Vetted Context</h4>
        <span className="text-[10px] text-[var(--text-subtle)]">{items.length} source{items.length === 1 ? '' : 's'}</span>
      </div>
      <div className="space-y-3">
        {items.map((item, idx) => {
          const title = typeof item.title === 'string' ? item.title : 'Source';
          const url = typeof item.url === 'string' ? item.url : '';
          const date = typeof item.date === 'string' ? item.date : typeof item.published === 'string' ? item.published : '';
          const summary = typeof item.summary === 'string' ? item.summary : typeof item.snippet === 'string' ? item.snippet : '';
          const keyFacts = Array.isArray(item.key_facts) ? item.key_facts : [];
          return (
            <div key={idx} className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3 text-sm text-[var(--text)]">
              <div className="flex flex-wrap items-center gap-2">
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer" className="font-semibold underline">
                    {title}
                  </a>
                ) : (
                  <span className="font-semibold">{title}</span>
                )}
                {date ? <span className="text-xs text-[var(--text-subtle)]">{date}</span> : null}
              </div>
              {summary ? <p className="mt-2 text-[15px] text-[var(--text)]">{summary}</p> : null}
              {keyFacts.length > 0 && (
                <ul className="mt-2 space-y-1 text-[14px] text-[var(--text-subtle)]">
                  {keyFacts.slice(0, 4).map((fact, i) => (
                    <li key={i}>• {fact}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Helper that fires onComplete once after mount (for non-typewriter cards). */
function CompletionTrigger({ onComplete }: { onComplete: () => void }) {
  const fired = useRef(false);
  useEffect(() => {
    if (!fired.current) {
      fired.current = true;
      onComplete();
    }
  }, [onComplete]);
  return null;
}
