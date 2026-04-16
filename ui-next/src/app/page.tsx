'use client';

import { useState, useRef, useCallback } from 'react';
import { useAppStore } from '@/stores/app-store';
import { usePipelineStream } from '@/hooks/usePipelineStream';
import { useServerStatus } from '@/hooks/useServerStatus';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useConversationHistory } from '@/hooks/useConversationHistory';
import { useScrollAnchor } from '@/hooks/useScrollAnchor';
import { Sidebar } from '@/components/layout/Sidebar';
import { Composer } from '@/components/layout/Composer';
import { ShortcutModal } from '@/components/layout/ShortcutModal';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { PhaseTimeline } from '@/components/layout/PhaseTimeline';

import { ChatFeed, ChatFeedMessage, RenderedPhase } from '@/components/chat/ChatFeed';
import { PhaseEvent, Conversation } from '@/lib/types';
import { METHOD_PHASES, DEFAULTS } from '@/lib/config';
import { buildMarkdownFromPhases } from '@/lib/markdown';
import { saveConversation } from '@/lib/db';
import { clearCache, searchWeb } from '@/lib/api-client';

export default function Home() {
  const running = useAppStore((s) => s.running);
  const setRunning = useAppStore((s) => s.setRunning);
  const method = useAppStore((s) => s.method);
  const composerText = useAppStore((s) => s.composerText);
  const setComposerText = useAppStore((s) => s.setComposerText);
  const isExpert = useAppStore((s) => s.isExpert);
  const isSequential = useAppStore((s) => s.isSequential);
  const isWebSearch = useAppStore((s) => s.isWebSearch);
  const isSmartSearch = useAppStore((s) => s.isSmartSearch);
  const getCurrentPreset = useAppStore((s) => s.getCurrentPreset);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);

  const { history, refresh: refreshHistory, remove: removeHistory } = useConversationHistory();
  const { startRun, stopRun } = usePipelineStream();
  const serverOnline = useServerStatus();
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatFeedMessage[]>([]);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const progressIdRef = useRef<string | null>(null);

  const [completedPhases, setCompletedPhases] = useState<number[]>([]);
  const [errorPhases, setErrorPhases] = useState<number[]>([]);
  const [currentPhase, setCurrentPhase] = useState<number | undefined>(undefined);
  const [phaseDurations, setPhaseDurations] = useState<Record<number, number>>({});
  const phaseStartTimesRef = useRef<Record<number, number>>({});

  const {
    scrollToBottom,
    showNewContentIndicator,
    dismissIndicator,
  } = useScrollAnchor(scrollContainerRef);

  useKeyboardShortcuts({
    onToggleSidebar: toggleSidebar,
    onShowShortcuts: () => setShortcutsOpen(true),
    onStop: () => {
      if (running) stopRun();
      setRunning(false);
    },
  });

  async function handleSubmit(providedText?: string) {
    const problem = (providedText ?? composerText).trim();
    if (!problem || running) return;

    setComposerText('');
    setRunning(true);
    setCompletedPhases([]);
    setErrorPhases([]);
    setCurrentPhase(undefined);
    setPhaseDurations({});
    phaseStartTimesRef.current = {};

    const userMsg: ChatFeedMessage = { id: 'u-' + Date.now(), role: 'user', content: problem };
    const assistantId = 'a-' + Date.now();
    const assistantMsg: ChatFeedMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      phases: [],
      isStreaming: true,
      currentPhaseName: undefined,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const progressId = 'prog-' + Date.now();
    progressIdRef.current = progressId;

    // ── Web Search mode (no LLM) ──
    if (isWebSearch) {
      const searchStart = performance.now();
      try {
        const data = await searchWeb(problem, 'general', 10, isSmartSearch);
        const hasGroups = data.results.some((r) => r.group);
        let md = '';
        if (hasGroups) {
          const byGroup: Record<string, typeof data.results> = {};
          data.results.forEach((r) => {
            const g = r.group || 'Results';
            byGroup[g] = byGroup[g] || [];
            byGroup[g].push(r);
          });
          md = Object.entries(byGroup)
            .map(([group, items]) => {
              const list = items
                .map((r, i) => {
                  const title = r.title || 'Source';
                  const url = r.url || '';
                  const snippet = r.snippet || r.content || '';
                  return `${i + 1}. [${title}](${url})\n   ${snippet}`;
                })
                .join('\n\n');
              return `**${group}**\n\n${list}`;
            })
            .join('\n\n---\n\n');
        } else {
          md = data.results
            .map((r, i) => {
              const title = r.title || 'Source';
              const url = r.url || '';
              const snippet = r.snippet || r.content || '';
              return `${i + 1}. [${title}](${url})\n   ${snippet}`;
            })
            .join('\n\n');
        }
        const searchDuration = (performance.now() - searchStart) / 1000;
        const resultContent = md || '*No results found.*';
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === assistantId);
          if (idx !== -1) {
            next[idx] = { ...next[idx], content: resultContent, isStreaming: false, duration: searchDuration };
          }
          return next;
        });
        await saveConversation({
          id: assistantId,
          timestamp: new Date().toISOString(),
          problem,
          phases: [],
          errors: [],
          preset: 'web-search',
          method: 'multi-perspective',
          total_tokens: null,
        });
        refreshHistory();
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Search failed';
        setMessages((prev) => {
          const next = [...prev];
          const idx = next.findIndex((m) => m.id === assistantId);
          if (idx !== -1) {
            next[idx] = { ...next[idx], content: `**Search error:** ${msg}`, isStreaming: false };
          }
          return next;
        });
      } finally {
        setRunning(false);
        progressIdRef.current = null;
      }
      return;
    }

    const isMultiPerspective = method === 'multi-perspective';
    const req = {
      problem,
      preset: getCurrentPreset(),
      top_k: isMultiPerspective ? 4 : (isExpert ? 4 : 2),
      sequential: isMultiPerspective ? false : !isSequential,
    };
    // eslint-disable-next-line no-console
    console.log('RunRequest payload:', req);

    const phases: RenderedPhase[] = [];
    let finalErrors: string[] = [];
    let finalTokens = { input: 0, output: 0, total: 0 };

    try {
      await startRun(req, (ev: PhaseEvent) => {
        if (ev.type === 'prompt_enhanced' && ev.enhanced) {
          setMessages((prev) => [
            ...prev,
            {
              id: 'info-enhance-' + Date.now(),
              role: 'info',
              content: `Prompt enhanced: "${ev.enhanced}"`,
              meta: { original: ev.original, enhanced: ev.enhanced },
            },
          ]);
        } else if (ev.type === 'phase_start' && typeof ev.phase === 'number') {
          const methodPhases = METHOD_PHASES[method] || METHOD_PHASES[DEFAULTS.method];
          const displayName = ev.name || methodPhases.find((p) => p.id === ev.phase)?.name || '';
          phaseStartTimesRef.current[ev.phase] = performance.now();
          setCurrentPhase(ev.phase);
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === assistantId);
            if (idx !== -1) {
              next[idx] = { ...next[idx], currentPhaseName: displayName };
            }
            return next;
          });
        } else if (ev.type === 'phase_complete' && typeof ev.phase === 'number') {
          const methodPhases = METHOD_PHASES[method] || METHOD_PHASES[DEFAULTS.method];
          const displayName = ev.name || methodPhases.find((p) => p.id === ev.phase)?.name || '';
          const phaseNum = ev.phase;
          const phaseData = ev.data ?? {};
          const renderedPhase: RenderedPhase = {
            index: phases.length,
            phase: phaseNum,
            name: displayName,
            data: phaseData,
          };
          phases.push(renderedPhase);
          const durationMs = performance.now() - (phaseStartTimesRef.current[phaseNum] ?? performance.now());
          setPhaseDurations((prev) => ({ ...prev, [phaseNum]: durationMs / 1000 }));
          setCompletedPhases((prev) => (prev.includes(phaseNum) ? prev : [...prev, phaseNum]));
          setCurrentPhase(undefined);

          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === assistantId);
            if (idx !== -1) {
              next[idx] = {
                ...next[idx],
                content: buildMarkdownFromPhases(phases),
                phases: [...phases],
                currentPhaseName: undefined,
              };
            }
            return next;
          });
        } else if (ev.type === 'phase_error' && typeof ev.phase === 'number') {
          setErrorPhases((prev) => (prev.includes(ev.phase!) ? prev : [...prev, ev.phase!]));
          setCurrentPhase(undefined);
        } else if (ev.type === 'error') {
          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === assistantId);
            if (idx !== -1) {
              next[idx] = { ...next[idx], isStreaming: false, currentPhaseName: undefined };
            }
            next.push({ id: 'err-' + Date.now(), role: 'error', content: ev.message || 'Pipeline error' });
            return next;
          });
          setCurrentPhase(undefined);
        } else if (ev.type === 'cancelled') {
          setMessages((prev) => [
            ...prev,
            { id: 'info-' + Date.now(), role: 'error', content: ev.message || 'Stopped by user' },
          ]);
          setCurrentPhase(undefined);
        } else if (ev.type === 'done') {
          finalErrors = ev.errors || [];
          finalTokens = ev.total_tokens || { input: 0, output: 0, total: 0 };
          setCurrentPhase(undefined);

          setMessages((prev) => {
            const next = [...prev];
            const idx = next.findIndex((m) => m.id === assistantId);
            if (idx !== -1) {
              next[idx] = {
                ...next[idx],
                content: buildMarkdownFromPhases(phases),
                phases: [...phases],
                isStreaming: false,
                currentPhaseName: undefined,
                tokens: finalTokens,
              };
            }
            if (finalErrors.length > 0) {
              next.push({ id: 'err-' + Date.now(), role: 'error', content: finalErrors.join('\n') });
            }
            return next;
          });

          const conv: Conversation = {
            id: Date.now().toString(),
            timestamp: new Date().toISOString(),
            problem,
            phases: phases.map((p) => ({ phase: p.phase, name: p.name, data: p.data })),
            errors: finalErrors,
            preset: getCurrentPreset(),
            method,
            total_tokens: finalTokens,
          };
          saveConversation(conv).then(refreshHistory).catch(console.error);
        }
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Connection error';
      setMessages((prev) => {
        const next = [...prev];
        const idx = next.findIndex((m) => m.id === assistantId);
        if (idx !== -1) {
          next[idx] = { ...next[idx], isStreaming: false };
        }
        next.push({ id: 'err-' + Date.now(), role: 'error', content: msg });
        return next;
      });
      setCurrentPhase(undefined);
    } finally {
      progressIdRef.current = null;
      setRunning(false);
    }
  }

  function handleStop() {
    stopRun();
    setRunning(false);
    setCurrentPhase(undefined);
  }

  function handleNew() {
    setMessages([]);
    setComposerText('');
    setCompletedPhases([]);
    setErrorPhases([]);
    setCurrentPhase(undefined);
    setPhaseDurations({});
    phaseStartTimesRef.current = {};
  }

  function handleLoad(conv: Conversation) {
    const renderedPhases: RenderedPhase[] = conv.phases.map((p, idx) => ({
      index: idx,
      phase: p.phase,
      name: p.name,
      data: p.data,
    }));
    const loaded: ChatFeedMessage[] = [
      { id: 'u-' + conv.id, role: 'user', content: conv.problem },
      {
        id: 'a-' + conv.id,
        role: 'assistant',
        content: buildMarkdownFromPhases(conv.phases),
        phases: renderedPhases,
        tokens: conv.total_tokens ?? undefined,
      },
    ];
    if (conv.errors.length > 0) {
      loaded.push({ id: 'err-' + conv.id, role: 'error', content: conv.errors.join('\n') });
    }
    setMessages(loaded);
    setCompletedPhases(renderedPhases.map((p) => p.phase));
    setErrorPhases([]);
    setCurrentPhase(undefined);
    setPhaseDurations({});
    phaseStartTimesRef.current = {};
  }

  async function handleClearCache() {
    await clearCache();
  }

  const hasMessages = messages.length > 0;
  const activeAssistantMsg = messages.find((m) => m.role === 'assistant' && m.isStreaming);

  return (
    <div className="flex h-screen w-full bg-[var(--bg)] text-[var(--text)]">
      <Sidebar
        conversations={history}
        onLoad={handleLoad}
        onDelete={removeHistory}
        onClear={handleClearCache}
        onNew={handleNew}
      />

      <div className="relative flex flex-1 flex-col sm:ml-0">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] px-4">
          <div className="flex items-center gap-3">
            <span className="font-semibold tracking-tight">ARA Chat</span>
            <div
              className={`h-2 w-2 rounded-full ${
                serverOnline === true
                  ? 'bg-green-500'
                  : serverOnline === false
                  ? 'bg-red-500'
                  : 'bg-yellow-500'
              }`}
              title={serverOnline === true ? 'Online' : serverOnline === false ? 'Offline' : 'Checking…'}
            />
          </div>
          <ThemeToggle />
        </header>

        {hasMessages && activeAssistantMsg && !isWebSearch && (
          <PhaseTimeline
            method={method}
            currentPhase={currentPhase}
            completedPhases={completedPhases}
            errorPhases={errorPhases}
            phaseDurations={phaseDurations}
          />
        )}

        <div ref={scrollContainerRef} className="relative flex-1 overflow-y-auto">
          {hasMessages ? (
            <>
              <ChatFeed
                messages={messages}
                onScrollToBottom={dismissIndicator}
                showNewContentIndicator={showNewContentIndicator}
              />
            </>
          ) : (
            <Composer running={running} onSubmit={() => handleSubmit()} onStop={handleStop} centered />
          )}
        </div>

        {hasMessages && <Composer running={running} onSubmit={() => handleSubmit()} onStop={handleStop} />}
      </div>

      <ShortcutModal isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}
