'use client';

import { useRef, useState, useEffect, useCallback } from 'react';
import { useAppStore } from '@/stores/app-store';
import { EXAMPLE_PROMPTS } from '@/lib/config';
import { cn } from '@/lib/utils';
import { isEnabled } from '@/hooks/useFeatureFlags';
import { ArrowUp, Sparkles, Plus, X, FileText, Image as ImageIcon, Upload } from 'lucide-react';

interface ComposerProps {
  running: boolean;
  onSubmit: () => void;
  onStop: () => void;
  centered?: boolean;
  isFollowup?: boolean;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'image/png',
  'image/jpeg',
  'image/jpg',
  'image/webp',
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export function Composer({ running, onSubmit, onStop, centered, isFollowup }: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const composerText = useAppStore((s) => s.composerText);
  const setComposerText = useAppStore((s) => s.setComposerText);
  const attachments = useAppStore((s) => s.attachments);
  const addAttachment = useAppStore((s) => s.addAttachment);
  const removeAttachment = useAppStore((s) => s.removeAttachment);
  const tier = useAppStore((s) => s.tier);
  const toggleTier = useAppStore((s) => s.toggleTier);
  const isImageMode = useAppStore((s) => s.isImageMode);
  const toggleImageMode = useAppStore((s) => s.toggleImageMode);
  const hasContent = composerText.trim().length > 0 || attachments.length > 0;

  const [estimate, setEstimate] = useState<{ tokens: number; cost: string; duration: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fetchEstimate = useCallback(async (text: string, preset: string) => {
    if (!text.trim() || text.trim().length < 3) {
      setEstimate(null);
      return;
    }
    try {
      const resp = await fetch('/api/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem: text, preset }),
      });
      if (!resp.ok) return;
      const data = await resp.json();
      setEstimate({
        tokens: (data.estimated_tokens_input || 0) + (data.estimated_tokens_output || 0),
        cost: data.estimated_cost_usd?.toFixed(3) || '0.000',
        duration: data.estimated_duration_seconds || 0,
      });
    } catch {
      setEstimate(null);
    }
  }, []);

  useEffect(() => {
    if (!isEnabled('cost-transparency')) return;
    const preset = tier === 'premium' ? 'auto-premium' : 'auto-budget';
    const timer = setTimeout(() => fetchEstimate(composerText, preset), 400);
    return () => clearTimeout(timer);
  }, [composerText, tier, fetchEstimate]);

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

  function processFiles(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) {
      if (attachments.length >= 5) {
        alert('Maximum 5 files allowed per message.');
        break;
      }
      if (file.size > MAX_FILE_SIZE) {
        alert(`File "${file.name}" exceeds 10MB limit.`);
        continue;
      }
      if (!ALLOWED_TYPES.includes(file.type)) {
        alert(`File type "${file.type}" not supported. Allowed: PDF, TXT, MD, PNG, JPG, WEBP.`);
        continue;
      }
      addAttachment(file);
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    processFiles(e.target.files);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  function handleDragOver(e: React.DragEvent) {
    if (!isEnabled('drag-drop')) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    if (!isEnabled('drag-drop')) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    if (!isEnabled('drag-drop')) return;
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    processFiles(e.dataTransfer.files);
  }

  function handlePaste(e: React.ClipboardEvent) {
    if (!isEnabled('drag-drop')) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    const files: File[] = [];
    for (const item of Array.from(items)) {
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length > 0) {
      e.preventDefault();
      for (const file of files) {
        if (attachments.length >= 5) {
          alert('Maximum 5 files allowed per message.');
          break;
        }
        if (file.size > MAX_FILE_SIZE) {
          alert(`File "${file.name}" exceeds 10MB limit.`);
          continue;
        }
        if (!ALLOWED_TYPES.includes(file.type)) {
          alert(`File type "${file.type}" not supported.`);
          continue;
        }
        addAttachment(file);
      }
    }
  }

  /** Attachment chip renderer */
  function AttachmentChip({ att }: { att: (typeof attachments)[0] }) {
    const isImage = att.type.startsWith('image/');
    return (
      <div className="group inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text)]">
        {isImage && att.previewUrl ? (
          <img src={att.previewUrl} alt={att.name} className="h-5 w-5 rounded object-cover" />
        ) : (
          <FileText className="h-4 w-4 shrink-0" />
        )}
        <span className="max-w-[120px] truncate">{att.name}</span>
        <span className="text-[10px] text-[var(--text-subtle)]">{formatFileSize(att.size)}</span>
        <button
          type="button"
          onClick={() => removeAttachment(att.id)}
          className="ml-1 rounded-full p-0.5 text-[var(--text-subtle)] transition-colors hover:bg-red-500/10 hover:text-red-500"
          aria-label={`Remove ${att.name}`}
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    );
  }

  /** Plus button to open file picker */
  function AttachButton() {
    return (
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={attachments.length >= 5 || running}
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-full border transition-colors',
          attachments.length >= 5 || running
            ? 'cursor-not-allowed border-[var(--border)] text-[var(--text-subtle)] opacity-40'
            : 'border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
        )}
        title="Attach files (PDF, TXT, MD, images)"
        aria-label="Attach files"
      >
        <Plus className="h-4 w-4" />
      </button>
    );
  }

  /** Tier toggle button — shared between centered and non-centered layouts */
  function TierToggle() {
    const isPremium = tier === 'premium';
    const tooltipText = estimate
      ? isPremium
        ? `Premium: ~$${estimate.cost} · Budget would be ~$${(parseFloat(estimate.cost) * 0.15).toFixed(3)}`
        : `Budget: ~$${estimate.cost} · Premium would be ~$${(parseFloat(estimate.cost) * 6.5).toFixed(3)}`
      : isPremium
        ? 'Premium mode active — click to switch to Budget'
        : 'Budget mode active — click to switch to Premium';

    return (
      <div className="group relative">
        <button
          type="button"
          onClick={toggleTier}
          className={cn(
            'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
            isPremium
              ? 'border-[var(--border-strong)] bg-[var(--surface-2)] text-[var(--text)]'
              : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
          )}
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Premium</span>
        </button>
        <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-max max-w-[220px] -translate-x-1/2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs text-[var(--text-muted)] opacity-0 shadow-[var(--shadow)] transition-opacity group-hover:opacity-100">
          {tooltipText}
          <div className="absolute left-1/2 top-full -mt-0.5 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-[var(--border)] bg-[var(--surface)]" />
        </div>
      </div>
    );
  }

  /** Image generation mode toggle */
  function ImageModeToggle() {
    return (
      <button
        type="button"
        onClick={toggleImageMode}
        className={cn(
          'flex h-8 items-center gap-1 rounded-full border px-3 text-xs font-medium transition-colors',
          isImageMode
            ? 'border-purple-500/50 bg-purple-500/10 text-purple-400'
            : 'border-[var(--border)] bg-transparent text-[var(--text-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
        )}
        title={isImageMode ? 'Image generation mode — click to switch to reasoning' : 'Generate an image — click to switch to image mode'}
      >
        <ImageIcon className="h-3.5 w-3.5" />
        <span>Image</span>
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

          <div
          className="relative rounded-3xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 shadow-[var(--shadow)] transition-shadow focus-within:shadow-[var(--shadow-lg)]"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onPaste={handlePaste}
        >
          {isDragging && (
            <div className="absolute inset-0 z-10 flex items-center justify-center rounded-3xl border-2 border-dashed border-[var(--accent)] bg-[var(--accent)]/5">
              <div className="flex items-center gap-2 text-sm font-medium text-[var(--accent)]">
                <Upload className="h-5 w-5" />
                Drop files here
              </div>
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={composerText}
            onChange={(e) => {
              setComposerText(e.target.value);
              autoResize();
            }}
            onKeyDown={handleKeyDown}
            placeholder={isImageMode ? 'Describe the image you want to generate...' : 'Ask anything...'}
            rows={1}
            className="w-full resize-none bg-transparent px-1 py-3 text-[17px] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none"
            style={{ minHeight: 120 }}
          />

            {/* Attachment chips — centered layout */}
            {attachments.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-2 px-1">
                {attachments.map((att) => (
                  <AttachmentChip key={att.id} att={att} />
                ))}
              </div>
            )}

            <div className="mt-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AttachButton />
                <TierToggle />
                <ImageModeToggle />
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
            {isImageMode ? 'Enter to generate image · Upload photos to use them as references · Shift+Enter for newline' : 'Enter to send · Shift+Enter for newline · Esc to stop · Max 5 files (10MB each)'}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
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
        <div
          className="relative rounded-3xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 shadow-[var(--shadow)] transition-shadow focus-within:shadow-[var(--shadow-lg)]"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onPaste={handlePaste}
        >
          {isDragging && (
            <div className="absolute inset-0 z-10 flex items-center justify-center rounded-3xl border-2 border-dashed border-[var(--accent)] bg-[var(--accent)]/5">
              <div className="flex items-center gap-2 text-sm font-medium text-[var(--accent)]">
                <Upload className="h-5 w-5" />
                Drop files here
              </div>
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={composerText}
            onChange={(e) => {
              setComposerText(e.target.value);
              autoResize();
            }}
            onKeyDown={handleKeyDown}
            placeholder={isImageMode ? 'Describe the new image and optionally attach reference photos...' : 'Ask anything...'}
            rows={1}
            className="w-full resize-none bg-transparent px-1 py-2 text-[17px] text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none"
            style={{ minHeight: 28 }}
          />

          {/* Attachment chips — bottom-bar layout */}
          {attachments.length > 0 && (
            <div className="mb-2 flex flex-wrap gap-2 px-1">
              {attachments.map((att) => (
                <AttachmentChip key={att.id} att={att} />
              ))}
            </div>
          )}

          <div className="mt-1 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AttachButton />
              <TierToggle />
              <ImageModeToggle />
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
          {isImageMode ? 'Enter to generate image · Upload photos to use them as references · Shift+Enter for newline' : 'Enter to send · Shift+Enter for newline · Esc to stop · Max 5 files (10MB each)'}
        </div>
        {isEnabled('cost-transparency') && estimate && (
          <div className="mt-1 text-center text-[10px] text-[var(--text-subtle)]">
            ~{estimate.tokens.toLocaleString()} tokens · ~${estimate.cost} · ~{estimate.duration}s
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />
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
