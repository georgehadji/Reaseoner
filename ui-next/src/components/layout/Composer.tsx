'use client';

import { useRef } from 'react';
import { useAppStore } from '@/stores/app-store';
import { EXAMPLE_PROMPTS } from '@/lib/config';
import { cn } from '@/lib/utils';
import { ArrowUp, Sparkles, Globe } from 'lucide-react';

interface ComposerProps {
  running: boolean;
  onSubmit: () => void;
  onStop: () => void;
  centered?: boolean;
  isFollowup?: boolean;
}

export function Composer({ running, onSubmit, onStop, centered, isFollowup }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composerText = useAppStore((s) => s.composerText);
  const setComposerText = useAppStore((s) => s.setComposerText);
  const tier = useAppStore((s) => s.tier);
  const toggleTier = useAppStore((s) => s.toggleTier);
  const isWebSearch = useAppStore((s) => s.isWebSearch);
  const toggleWebSearch = useAppStore((s) => s.toggleWebSearch);



  const hasContent = composerText.trim().length > 0;

  function autoResize() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (running) onStop();
      else onSubmit();
    } else if (e.key === 'Escape') {
      onStop();
    }
  }

  /** Tier toggle button — shared between centered and non-centered layouts */
  function TierToggle() {
    const isPremium = tier === 'premium';
    return (
      <button
        type="button"
        disabled={isWebSearch}
        onClick={toggleTier}
        className={cn(
          'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
          isPremium
            ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
            : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
          isWebSearch && 'opacity-40 cursor-not-allowed'
        )}
        title={isPremium ? 'Premium mode active — click to switch to Budget' : 'Budget mode active — click to switch to Premium'}
      >
        <Sparkles className="h-3.5 w-3.5" />
        <span>Premium</span>
      </button>
    );
  }

  if (centered) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center px-4">
        <div className="w-full max-w-3xl">
          <h1 className="mb-6 text-center text-2xl font-semibold tracking-tight text-[var(--text)] sm:text-3xl">
            What would you like to solve?
          </h1>

          <div className="relative rounded-3xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 shadow-[var(--shadow)] transition-shadow focus-within:shadow-[var(--shadow-lg)]">
            <textarea
              ref={textareaRef}
              value={composerText}
              onChange={(e) => {
                setComposerText(e.target.value);
                autoResize();
              }}
              onKeyDown={handleKeyDown}
              placeholder={isWebSearch ? 'Search the web...' : 'Ask anything...'}
              rows={1}
              className="w-full resize-none bg-transparent px-1 py-3 text-[17px] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none"
              style={{ minHeight: 120 }}
            />

            <div className="mt-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TierToggle />

                <button
                  type="button"
                  onClick={toggleWebSearch}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                    isWebSearch
                      ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                      : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                  )}
                  title="Web search with LLM-powered decomposition"
                >
                  <Globe className="h-3.5 w-3.5" />
                  {isWebSearch ? 'Web Search' : 'Web'}
                </button>


              </div>

              {running ? (
                <button
                  type="button"
                  onClick={onStop}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-red-500/20 text-red-500 transition-colors hover:bg-red-500/30"
                  aria-label="Stop"
                >
                  <span className="h-2.5 w-2.5 rounded-sm bg-current" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onSubmit}
                  disabled={!hasContent}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-text)] transition-opacity hover:opacity-90 disabled:opacity-40"
                  aria-label="Send"
                >
                  <ArrowUp className="h-5 w-5" />
                </button>
              )}
            </div>
          </div>

          <div className="mt-2 text-center text-xs text-[var(--text-subtle)]">
            Enter to send · Shift+Enter for newline · Esc to stop
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full px-4 pb-6 pt-2">
      <div className="mx-auto max-w-3xl">
        {isFollowup && !centered && (
          <div className="mb-2 flex flex-wrap items-center gap-2 px-1">
            <span className="rounded-full border border-[var(--border-strong)] bg-[var(--accent)]/10 px-2 py-0.5 text-xs font-medium text-[var(--accent)]">
              Follow-up
            </span>
            <span className="max-w-full break-words text-xs text-[var(--text-subtle)]">
              Continuing previous conversation
            </span>
          </div>
        )}
        {isWebSearch && (
          <div className="mb-2 flex flex-wrap items-center gap-2 px-1">
            <span className="text-xs font-medium text-[var(--text-muted)]">Web Search</span>
            <span className="max-w-full break-words text-xs text-[var(--text-subtle)]">
              Advanced web search with LLM processing.
            </span>
          </div>
        )}

        <div className="relative rounded-3xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 shadow-[var(--shadow)] transition-shadow focus-within:shadow-[var(--shadow-lg)]">
          <textarea
            ref={textareaRef}
            value={composerText}
            onChange={(e) => {
              setComposerText(e.target.value);
              autoResize();
            }}
            onKeyDown={handleKeyDown}
            placeholder={isWebSearch ? 'Search the web...' : 'Ask anything...'}
            rows={1}
            className="w-full resize-none bg-transparent px-1 py-2 text-[17px] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none"
            style={{ minHeight: 28 }}
          />

          <div className="mt-1 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TierToggle />

              <button
                type="button"
                onClick={toggleWebSearch}
                className={cn(
                  'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                  isWebSearch
                    ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                    : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                )}
                title="Web search with LLM-powered decomposition"
              >
                <Globe className="h-3.5 w-3.5" />
                {isWebSearch ? 'Web Search' : 'Web'}
              </button>


            </div>

            {running ? (
              <button
                type="button"
                onClick={onStop}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-red-500/20 text-red-500 transition-colors hover:bg-red-500/30"
                aria-label="Stop"
              >
                <span className="h-2.5 w-2.5 rounded-sm bg-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onSubmit}
                disabled={!hasContent}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-[var(--accent-text)] transition-opacity hover:opacity-90 disabled:opacity-40"
                aria-label="Send"
              >
                <ArrowUp className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-2 text-center text-xs text-[var(--text-subtle)]">
          Enter to send · Shift+Enter for newline · Esc to stop
        </div>
      </div>
    </div>
  );
}

function ExampleChip({ text }: { text: string }) {
  return (
    <button
      type="button"
      onClick={() => {
        useAppStore.getState().setComposerText(text);
      }}
      className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--text)]"
    >
      {text}
    </button>
  );
}
