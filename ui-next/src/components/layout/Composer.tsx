'use client';

import { useRef, useState, useEffect } from 'react';
import { useAppStore } from '@/stores/app-store';
import { METHOD_PRESETS, METHOD_CONTROLS, METHODS, METHOD_EXAMPLES } from '@/lib/config';
import { METHOD_HINTS_DATA } from '@/lib/method-hints';
import { cn } from '@/lib/utils';
import { ArrowUp, ChevronDown, Sparkles, Globe, Zap, Wand2 } from 'lucide-react';

interface ComposerProps {
  running: boolean;
  onSubmit: () => void;
  onStop: () => void;
  centered?: boolean;
  isFollowup?: boolean;
}

export function Composer({ running, onSubmit, onStop, centered, isFollowup }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const composerText = useAppStore((s) => s.composerText);
  const setComposerText = useAppStore((s) => s.setComposerText);
  const method = useAppStore((s) => s.method);
  const presetIndex = useAppStore((s) => s.presetIndex);
  const cyclePreset = useAppStore((s) => s.cyclePreset);
  const isSequential = useAppStore((s) => s.isSequential);
  const toggleSequential = useAppStore((s) => s.toggleSequential);
  const isExpert = useAppStore((s) => s.isExpert);
  const toggleExpert = useAppStore((s) => s.toggleExpert);
  const isWebSearch = useAppStore((s) => s.isWebSearch);
  const toggleWebSearch = useAppStore((s) => s.toggleWebSearch);
  const isSmartSearch = useAppStore((s) => s.isSmartSearch);
  const toggleSmartSearch = useAppStore((s) => s.toggleSmartSearch);
  const isEnhancePrompt = useAppStore((s) => s.isEnhancePrompt);
  const toggleEnhancePrompt = useAppStore((s) => s.toggleEnhancePrompt);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    if (!dropdownOpen) return;
    function onMouseDown(e: MouseEvent) {
      if (!dropdownRef.current) return;
      if (!dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setDropdownOpen(false);
    }
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [dropdownOpen]);

  const hasContent = composerText.trim().length > 0;
  const presets = METHOD_PRESETS[method] || METHOD_PRESETS['multi-perspective'];
  const currentPreset = presets[Math.min(presetIndex, presets.length - 1)];
  const controls = METHOD_CONTROLS[method] || [];

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
              placeholder={
                isWebSearch
                  ? 'Search the web...'
                  : 'Ask anything...'
              }
              rows={1}
              className="w-full resize-none bg-transparent px-1 py-3 text-[17px] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none"
              style={{ minHeight: 120 }}
            />

            <div className="mt-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                {/* Method Dropdown */}
                <div ref={dropdownRef} className="relative">
                  <button
                    type="button"
                    disabled={isWebSearch}
                    onClick={() => setDropdownOpen((v) => !v)}
                    className={cn(
                      'flex h-8 items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 text-xs font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]',
                      isWebSearch && 'opacity-40 cursor-not-allowed'
                    )}
                  >
                    <span>{METHODS.find((m) => m.id === method)?.name}</span>
                    <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                  </button>
                  {dropdownOpen && (
                    <div className="absolute bottom-full left-0 z-[100] mb-2 max-h-64 w-56 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-lg)]">
                      {METHODS.map((m) => (
                        <button
                          type="button"
                          key={m.id}
                          onClick={() => {
                            useAppStore.getState().setMethod(m.id);
                            setDropdownOpen(false);
                          }}
                          className={cn(
                            'flex w-full flex-col gap-0.5 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--surface-2)]',
                            method === m.id && 'bg-[var(--surface-2)]'
                          )}
                          title={m.description}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[var(--text)]">{m.name}</span>
                            <span className="text-xs text-[var(--text-subtle)]">
                              {'$'.repeat(m.cost)}
                            </span>
                          </div>
                          <span className="text-xs text-[var(--text-muted)]">{m.description}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {controls.includes('budget') && (
                  <button
                    type="button"
                    disabled={isWebSearch}
                    onClick={cyclePreset}
                    className={cn(
                      'flex h-8 items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 text-xs font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]',
                      isWebSearch && 'opacity-40 cursor-not-allowed'
                    )}
                    title="Switch preset"
                  >
                    <Sparkles className="h-3.5 w-3.5 text-[var(--text-subtle)]" />
                    <span>{currentPreset?.label}</span>
                  </button>
                )}

                {controls.includes('parallel') && (
                  <button
                    type="button"
                    disabled={isWebSearch}
                    onClick={toggleSequential}
                    className={cn(
                      'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                      isSequential
                        ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                        : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
                      isWebSearch && 'opacity-40 cursor-not-allowed'
                    )}
                    title="Sequential vs Parallel"
                  >
                    {isSequential ? 'Sequential' : 'Parallel'}
                  </button>
                )}

                {controls.includes('expert') && (
                  <button
                    type="button"
                    disabled={isWebSearch}
                    onClick={toggleExpert}
                    className={cn(
                      'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                      isExpert
                        ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                        : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
                      isWebSearch && 'opacity-40 cursor-not-allowed'
                    )}
                    title="Expert mode"
                  >
                    Expert
                  </button>
                )}

                <button
                  type="button"
                  disabled={isWebSearch}
                  onClick={toggleEnhancePrompt}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                    isEnhancePrompt
                      ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                      : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
                    isWebSearch && 'opacity-40 cursor-not-allowed'
                  )}
                  title="Rewrite prompt for clarity and context"
                >
                  <Wand2 className="h-3.5 w-3.5" />
                  {isEnhancePrompt ? 'Enhance' : 'Enhance'}
                </button>

                <button
                  type="button"
                  onClick={toggleWebSearch}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                    isWebSearch
                      ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                      : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                  )}
                  title="Web Search (no LLM)"
                >
                  <Globe className="h-3.5 w-3.5" />
                  {isWebSearch ? 'Web Search' : 'Web'}
                </button>

                {isWebSearch && (
                  <button
                    type="button"
                    onClick={toggleSmartSearch}
                    className={cn(
                      'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                      isSmartSearch
                        ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                        : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                    )}
                    title="Decompose query into focused searches using a lightweight LLM"
                  >
                    <Zap className="h-3.5 w-3.5" />
                    Smart
                  </button>
                )}
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

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {(METHOD_EXAMPLES[method] || METHOD_EXAMPLES['multi-perspective']).map((text) => (
              <ExampleChip key={text} text={text} />
            ))}
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
        {/* Method hint pill */}
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
        {isWebSearch ? (
          <div className="mb-2 flex flex-wrap items-center gap-2 px-1">
            <span className="text-xs font-medium text-[var(--text-muted)]">Web Search</span>
            <span className="max-w-full break-words text-xs text-[var(--text-subtle)]">
              {isSmartSearch
                ? 'Advanced web search with LLM processing.'
                : 'Advanced web search without LLM processing.'}
            </span>
          </div>
        ) : METHOD_HINTS_DATA[method] && !isFollowup ? (
          <div className="mb-2 flex flex-wrap items-center gap-2 px-1">
            <span className="text-xs font-medium text-[var(--text-muted)]">
              {METHOD_HINTS_DATA[method].title}
            </span>
            <span className="max-w-full break-words text-xs text-[var(--text-subtle)]">
              {METHOD_HINTS_DATA[method].desc}
            </span>
          </div>
        ) : null}

        <div className="relative rounded-3xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 shadow-[var(--shadow)] transition-shadow focus-within:shadow-[var(--shadow-lg)]">
          <textarea
            ref={textareaRef}
            value={composerText}
            onChange={(e) => {
              setComposerText(e.target.value);
              autoResize();
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              centered
                ? isWebSearch
                  ? 'Search the web...'
                  : 'What would you like to solve?'
                : isWebSearch
                  ? 'Search the web...'
                  : 'Ask anything...'
            }
            rows={1}
            className="w-full resize-none bg-transparent px-1 py-2 text-[17px] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none"
            style={{ minHeight: centered ? 120 : 28 }}
          />

          <div className="mt-1 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {/* Method Dropdown */}
              <div ref={dropdownRef} className="relative">
                <button
                  type="button"
                  disabled={isWebSearch}
                  onClick={() => setDropdownOpen((v) => !v)}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 text-xs font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]',
                    isWebSearch && 'opacity-40 cursor-not-allowed'
                  )}
                >
                  <span>{METHODS.find((m) => m.id === method)?.name}</span>
                  <ChevronDown className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                </button>
                {dropdownOpen && (
                  <div className="absolute bottom-full left-0 z-[100] mb-2 max-h-64 w-56 overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-1 shadow-[var(--shadow-lg)]">
                    {METHODS.map((m) => (
                      <button
                        type="button"
                        key={m.id}
                        onClick={() => {
                          useAppStore.getState().setMethod(m.id);
                          setDropdownOpen(false);
                        }}
                        className={cn(
                          'flex w-full flex-col gap-0.5 rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--surface-2)]',
                          method === m.id && 'bg-[var(--surface-2)]'
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text)]">{m.name}</span>
                          <span className="text-xs text-[var(--text-subtle)]">
                            {'$'.repeat(m.cost)}
                          </span>
                        </div>
                        <span className="text-xs text-[var(--text-muted)]">{m.description}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {controls.includes('budget') && (
                <button
                  type="button"
                  disabled={isWebSearch}
                  onClick={cyclePreset}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-3 text-xs font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]',
                    isWebSearch && 'opacity-40 cursor-not-allowed'
                  )}
                  title="Switch preset"
                >
                  <Sparkles className="h-3.5 w-3.5 text-[var(--text-subtle)]" />
                  <span>{currentPreset?.label}</span>
                </button>
              )}

              {controls.includes('parallel') && (
                <button
                  type="button"
                  disabled={isWebSearch}
                  onClick={toggleSequential}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                    isSequential
                      ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                      : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
                    isWebSearch && 'opacity-40 cursor-not-allowed'
                  )}
                  title="Sequential vs Parallel"
                >
                  {isSequential ? 'Sequential' : 'Parallel'}
                </button>
              )}

              {controls.includes('expert') && (
                <button
                  type="button"
                  disabled={isWebSearch}
                  onClick={toggleExpert}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                    isExpert
                      ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                      : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
                    isWebSearch && 'opacity-40 cursor-not-allowed'
                  )}
                  title="Expert mode"
                >
                  Expert
                </button>
              )}

              <button
                type="button"
                disabled={isWebSearch}
                onClick={toggleEnhancePrompt}
                className={cn(
                  'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                  isEnhancePrompt
                    ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                    : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
                  isWebSearch && 'opacity-40 cursor-not-allowed'
                )}
                title="Rewrite prompt for clarity and context"
              >
                <Wand2 className="h-3.5 w-3.5" />
                {isEnhancePrompt ? 'Enhance' : 'Enhance'}
              </button>

              <button
                type="button"
                onClick={toggleWebSearch}
                className={cn(
                  'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                  isWebSearch
                    ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                    : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                )}
                title="Web Search (no LLM)"
              >
                <Globe className="h-3.5 w-3.5" />
                {isWebSearch ? 'Web Search' : 'Web'}
              </button>

              {isWebSearch && (
                <button
                  type="button"
                  onClick={toggleSmartSearch}
                  className={cn(
                    'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
                    isSmartSearch
                      ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
                      : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
                  )}
                  title="Decompose query into focused searches using a lightweight LLM"
                >
                  <Zap className="h-3.5 w-3.5" />
                  Smart
                </button>
              )}
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
