'use client';

import { useState, useCallback } from 'react';
import { Copy, Check, Sparkles, Clock } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { MarkdownRenderer } from './MarkdownRenderer';
import { PhaseRenderer } from '@/components/phases/PhaseRenderer';
import { ErrorMessage } from './ErrorMessage';
import { TokenCount } from '@/lib/types';
import { copyToClipboard } from '@/lib/utils';

export interface RenderedPhase {
  index: number;
  phase: number;
  name: string;
  data: unknown;
}

export interface ChatFeedMessage {
  id: string;
  role: 'user' | 'assistant' | 'error' | 'info';
  content: string;
  phases?: RenderedPhase[];
  isStreaming?: boolean;
  currentPhaseName?: string;
  tokens?: TokenCount;
  duration?: number;
  meta?: { original?: string; enhanced?: string };
  activeAgents?: { name: string; task: string }[];
  streamingContent?: string;
  phaseModels?: string[];
}

interface ChatFeedProps {
  messages: ChatFeedMessage[];
  onScrollToBottom?: () => void;
  showNewContentIndicator?: boolean;
}

function PhaseIndicator({
  name,
  agents,
  models,
}: {
  name?: string;
  agents?: { name: string; task: string }[];
  models?: string[];
}) {
  return (
    <div className="mb-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1">
          <span
            className="h-2 w-2 animate-bounce rounded-full bg-[var(--text-muted)]"
            style={{ animationDelay: '0ms' }}
          />
          <span
            className="h-2 w-2 animate-bounce rounded-full bg-[var(--text-muted)]"
            style={{ animationDelay: '150ms' }}
          />
          <span
            className="h-2 w-2 animate-bounce rounded-full bg-[var(--text-muted)]"
            style={{ animationDelay: '300ms' }}
          />
        </div>
        {name ? (
          <span className="text-xs font-medium text-[var(--text-muted)]">
            Running {name}…
          </span>
        ) : null}
      </div>
      {models && models.length > 0 && (
        <div className="flex flex-wrap gap-1 pl-6">
          {models.map((m) => (
            <span
              key={m}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-subtle)]"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              {m.split('/').pop() || m}
            </span>
          ))}
        </div>
      )}
      {agents && agents.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-6">
          {agents.map((a) => (
            <span
              key={a.name}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-subtle)]"
              title={a.task}
            >
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" />
              {a.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}m ${secs.toString().padStart(2, '0')}s`;
}

function MessageActions({ content, tokens, duration }: { content: string; tokens?: TokenCount; duration?: number }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    const ok = await copyToClipboard(content);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const showTokens = tokens && (tokens.total ?? 0) > 0;

  return (
    <div className="mt-2 flex items-center justify-center gap-3">
      <button
        type="button"
        onClick={handleCopy}
        className="flex items-center gap-1 text-xs text-[var(--text-subtle)] transition-colors hover:text-[var(--text)]"
        aria-label="Copy response"
      >
        {copied ? (
          <>
            <Check className="h-3.5 w-3.5" /> Copied
          </>
        ) : (
          <>
            <Copy className="h-3.5 w-3.5" /> Copy
          </>
        )}
      </button>
      {duration !== undefined && duration > 0 ? (
        <span className="inline-flex items-center gap-1 rounded-full bg-[var(--surface-2)] px-2 py-0.5 text-xs font-medium text-[var(--text-muted)]">
          <Clock className="h-3 w-3" />
          {formatDuration(duration)}
        </span>
      ) : null}
      {showTokens ? (
        <span className="text-xs text-[var(--text-subtle)]">
          {tokens.input.toLocaleString()} in · {tokens.output.toLocaleString()} out · {tokens.total.toLocaleString()} total
        </span>
      ) : null}
    </div>
  );
}

export function ChatFeed({
  messages,
  onScrollToBottom,
  showNewContentIndicator,
}: ChatFeedProps) {
  // Track how many phases are allowed to render for each assistant message.
  // Key: message id, Value: number of visible phases (default 1 so first phase shows immediately)
  const [visiblePhaseCounts, setVisiblePhaseCounts] = useState<Record<string, number>>({});

  const handlePhaseComplete = useCallback((msgId: string, phaseIndex: number) => {
    setVisiblePhaseCounts((prev) => {
      const current = prev[msgId] ?? 1;
      // Only advance if this is the currently visible phase
      if (phaseIndex === current - 1) {
        return { ...prev, [msgId]: current + 1 };
      }
      return prev;
    });
  }, []);

  return (
    <div className="relative flex flex-col gap-5 px-4 py-6 sm:px-6 lg:px-8">
      {messages.map((msg) => {
        if (msg.role === 'user') {
          return (
            <ChatMessage key={msg.id} role="user">
              {msg.content}
            </ChatMessage>
          );
        }
        if (msg.role === 'error') {
          return (
            <div key={msg.id} className="flex w-full justify-start">
              <ErrorMessage content={msg.content} />
            </div>
          );
        }
        if (msg.role === 'info') {
          const isEnhancedPrompt = msg.meta?.enhanced;
          if (isEnhancedPrompt) {
            return (
              <div key={msg.id} className="flex w-full justify-center px-4">
                <div className="w-full max-w-3xl rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
                  <div className="mb-2 flex items-center gap-2 text-xs font-medium text-[var(--text-muted)]">
                    <Sparkles className="h-3.5 w-3.5" />
                    Prompt Enhanced
                  </div>
                  <div className="mb-2 text-sm text-[var(--text-subtle)] line-through opacity-70">
                    {msg.meta?.original}
                  </div>
                  <div className="text-sm font-medium text-[var(--text)]">
                    {msg.meta?.enhanced}
                  </div>
                </div>
              </div>
            );
          }
          return (
            <div key={msg.id} className="flex w-full justify-center">
              <div className="max-w-3xl rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-4 py-2 text-xs text-[var(--text-subtle)]">
                {msg.content}
              </div>
            </div>
          );
        }

        const visibleCount = visiblePhaseCounts[msg.id] ?? 1;
        const phases = msg.phases || [];
        const visiblePhases = phases.slice(0, visibleCount);

        return (
          <div key={msg.id} className="flex w-full flex-col items-center">
            <ChatMessage role="assistant">
              {msg.isStreaming && (
                <PhaseIndicator
                  name={msg.currentPhaseName}
                  agents={msg.activeAgents}
                  models={msg.phaseModels}
                />
              )}
              {msg.streamingContent ? (
                <div className="w-full max-w-3xl whitespace-pre-wrap text-[18px] leading-relaxed text-[var(--text)]">
                  {msg.streamingContent}
                  <span className="inline-block h-[1em] w-0.5 animate-pulse bg-[var(--accent)] align-middle" />
                </div>
              ) : phases.length > 0 ? (
                <div className="w-full">
                  {visiblePhases.map((phase, idx) => (
                    <PhaseRenderer
                      key={`${msg.id}-${phase.phase}`}
                      phase={phase}
                      onComplete={() => handlePhaseComplete(msg.id, idx)}
                      animationKey={`${msg.id}-${phase.index}`}
                    />
                  ))}
                </div>
              ) : (
                <MarkdownRenderer>{msg.content || ' '}</MarkdownRenderer>
              )}
            </ChatMessage>
            {!msg.isStreaming && msg.role === 'assistant' && (
              <MessageActions content={msg.content} tokens={msg.tokens} duration={msg.duration} />
            )}
          </div>
        );
      })}

      {showNewContentIndicator && (
        <button
          type="button"
          onClick={onScrollToBottom}
          className="fixed bottom-24 left-1/2 z-30 -translate-x-1/2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-medium text-[var(--text)] shadow-[var(--shadow-lg)] transition-colors hover:bg-[var(--surface-2)]"
        >
          New content below ↓
        </button>
      )}
    </div>
  );
}
