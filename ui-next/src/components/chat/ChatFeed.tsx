'use client';

import { useState } from 'react';
import { Copy, Check, Sparkles } from 'lucide-react';
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
}

interface ChatFeedProps {
  messages: ChatFeedMessage[];
  onScrollToBottom?: () => void;
  showNewContentIndicator?: boolean;
}

function PhaseIndicator({ name }: { name?: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
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
  );
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
        <span className="text-xs text-[var(--text-subtle)]">{duration.toFixed(1)}s</span>
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
        return (
          <div key={msg.id} className="flex w-full flex-col items-center">
            <ChatMessage role="assistant">
              {msg.isStreaming && <PhaseIndicator name={msg.currentPhaseName} />}
              {msg.phases && msg.phases.length > 0 ? (
                <div className="w-full">
                  {msg.phases.map((phase) => (
                    <PhaseRenderer key={`${msg.id}-${phase.phase}`} phase={phase} />
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
