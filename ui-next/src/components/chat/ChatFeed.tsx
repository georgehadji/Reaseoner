'use client';

import { useState, useCallback } from 'react';
import { Copy, Check, Sparkles, Clock, FileText, Image as ImageIcon, Wand2 } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { MarkdownRenderer } from './MarkdownRenderer';
import { PhaseRenderer } from '@/components/phases/PhaseRenderer';
import { ErrorMessage } from './ErrorMessage';
import { TokenCount, Attachment } from '@/lib/types';
import { TIMING } from '@/lib/config';
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
  attachments?: Attachment[];
  phases?: RenderedPhase[];
  isStreaming?: boolean;
  animated?: boolean; // false = skip typewriter effect (e.g. loaded history)
  currentPhaseName?: string;
  tokens?: TokenCount;
  duration?: number;
  meta?: { original?: string; enhanced?: string };
  activeAgents?: { name: string; task: string }[];
  streamingContent?: string;
  phaseModels?: string[];
  imageData?: string; // base64 data URL for generated images
  images?: { data: string; model?: string }[]; // multiple generated images
  loadingKind?: 'image-generation';
  loadingPrompt?: string;
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
          {TIMING.streamingBounceDelays.map((delay) => (
            <span
              key={delay}
              className="h-2 w-2 animate-bounce rounded-full bg-[var(--text-muted)]"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
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

function ImageGenerationIndicator({ prompt }: { prompt?: string }) {
  return (
    <div className="mb-2 w-full max-w-3xl overflow-hidden rounded-[28px] border border-[var(--border)] bg-[linear-gradient(135deg,rgba(255,196,132,0.18),rgba(255,255,255,0.88)_38%,rgba(143,212,255,0.2))] p-4 shadow-[var(--shadow)]">
      <div className="relative overflow-hidden rounded-[24px] border border-white/50 bg-[var(--surface)]/80 p-5 backdrop-blur">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,191,117,0.18),transparent_42%),radial-gradient(circle_at_bottom_right,rgba(104,185,255,0.16),transparent_38%)]" />

        <div className="relative mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">
            <Wand2 className="h-3.5 w-3.5" />
            Rendering Image
          </div>
          <div className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/70 px-2.5 py-1 text-[10px] font-medium text-[var(--text-subtle)]">
            <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
            Multi-model
          </div>
        </div>

        <div className="relative mx-auto mb-5 flex h-56 w-full max-w-xl items-center justify-center">
          <div className="absolute h-40 w-40 animate-spin rounded-full border border-dashed border-sky-300/70" style={{ animationDuration: '14s' }} />
          <div className="absolute h-28 w-28 animate-spin rounded-full border border-dashed border-amber-300/80" style={{ animationDuration: '10s', animationDirection: 'reverse' }} />
          <div className="absolute -translate-x-8 translate-y-3 rotate-[-10deg] rounded-[24px] border border-white/70 bg-white/80 p-4 shadow-lg backdrop-blur">
            <div className="flex h-28 w-28 items-center justify-center rounded-[18px] bg-[linear-gradient(145deg,rgba(255,210,148,0.28),rgba(255,255,255,0.9),rgba(157,219,255,0.28))]">
              <ImageIcon className="h-10 w-10 animate-pulse text-[var(--text-muted)]" />
            </div>
          </div>
          <div className="absolute translate-x-10 -translate-y-4 rotate-[8deg] rounded-[24px] border border-white/70 bg-white/75 p-4 shadow-lg backdrop-blur">
            <div className="h-28 w-28 rounded-[18px] bg-[linear-gradient(135deg,rgba(255,255,255,0.25),rgba(255,196,132,0.45),rgba(143,212,255,0.4))]">
              <div className="flex h-full w-full items-end justify-between p-3">
                {[0, 120, 240].map((delay) => (
                  <span
                    key={delay}
                    className="h-3 w-3 animate-bounce rounded-full bg-white/90"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
          {[0, 1, 2, 3].map((i) => (
            <Sparkles
              key={i}
              className="absolute h-4 w-4 animate-pulse text-amber-400"
              style={{
                top: `${18 + i * 18}%`,
                left: i % 2 === 0 ? `${16 + i * 12}%` : undefined,
                right: i % 2 === 1 ? `${14 + i * 10}%` : undefined,
                animationDelay: `${i * 180}ms`,
              }}
            />
          ))}
        </div>

        <div className="relative space-y-3">
          <div className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-[linear-gradient(90deg,#f59e0b,#fb7185,#38bdf8)]" />
          </div>
          <div className="flex items-center justify-between gap-3 text-xs text-[var(--text-subtle)]">
            <span>Expanding prompt, testing providers, decoding the first valid image.</span>
            <span className="font-medium text-[var(--text-muted)]">Working…</span>
          </div>
          {prompt ? (
            <div className="rounded-2xl border border-[var(--border)] bg-white/70 px-4 py-3 text-sm text-[var(--text)]">
              <span className="mr-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Prompt</span>
              {prompt}
            </div>
          ) : null}
        </div>
      </div>
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
      setTimeout(() => setCopied(false), TIMING.copiedFeedbackMs);
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
          {(tokens.input ?? 0).toLocaleString()} in · {(tokens.output ?? 0).toLocaleString()} out · {(tokens.total ?? 0).toLocaleString()} total
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
            <div key={msg.id} className="flex w-full flex-col items-end gap-2">
              {msg.attachments && msg.attachments.length > 0 && (
                <div className="flex flex-wrap justify-end gap-2 px-1">
                  {msg.attachments.map((att) => (
                    <div
                      key={att.id}
                      className="inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs text-[var(--text-muted)]"
                    >
                      {att.previewUrl ? (
                        <img src={att.previewUrl} alt={att.name} className="h-5 w-5 rounded object-cover" />
                      ) : (
                        <FileText className="h-4 w-4 shrink-0" />
                      )}
                      <span className="max-w-[120px] truncate">{att.name}</span>
                      <span className="text-[10px] text-[var(--text-subtle)]">
                        {(att.size / 1024 / 1024).toFixed(1)}MB
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <ChatMessage role="user">{msg.content}</ChatMessage>
            </div>
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
              {msg.loadingKind === 'image-generation' ? (
                <ImageGenerationIndicator prompt={msg.loadingPrompt} />
              ) : msg.isStreaming && (
                <PhaseIndicator
                  name={msg.currentPhaseName}
                  agents={msg.activeAgents}
                  models={msg.phaseModels}
                />
              )}
              {msg.imageData && (
                <div className="mb-4 w-full max-w-3xl">
                  <img
                    src={msg.imageData}
                    alt="Generated image"
                    className="max-h-[600px] rounded-xl border border-[var(--border)] object-contain shadow-[var(--shadow)]"
                    loading="lazy"
                  />
                </div>
              )}
              {msg.images && msg.images.length > 0 && (
                <div className="mb-4 grid w-full max-w-4xl gap-4 sm:grid-cols-2">
                  {msg.images.map((img, idx) => (
                    <figure
                      key={idx}
                      className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-2)] shadow-[var(--shadow)]"
                    >
                      <img
                        src={img.data}
                        alt={`Generated image ${idx + 1}`}
                        className="h-full w-full max-h-[520px] object-contain"
                        loading="lazy"
                      />
                      {img.model ? (
                        <figcaption className="border-t border-[var(--border)] px-3 py-2 text-xs text-[var(--text-subtle)]">
                          LLM model: {img.model}
                        </figcaption>
                      ) : null}
                    </figure>
                  ))}
                </div>
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
                      animated={msg.animated !== false}
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
