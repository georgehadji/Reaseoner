'use client';

import { useState } from 'react';
import { X, Copy, Check, AlertTriangle, AlertCircle } from 'lucide-react';
import { copyToClipboard } from '@/lib/utils';

interface ErrorMessageProps {
  content: string;
}

function isWarningContent(content: string): boolean {
  return /warning|citation integrity|vetting flags|skipped|ignored/i.test(content);
}

export function ErrorMessage({ content }: ErrorMessageProps) {
  const [dismissed, setDismissed] = useState(false);
  const [copied, setCopied] = useState(false);
  const isWarning = isWarningContent(content);

  async function handleCopy() {
    const ok = await copyToClipboard(content);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  if (dismissed) return null;

  return (
    <div
      className={`max-w-[85%] rounded-2xl border px-4 py-3 text-sm sm:max-w-[75%] ${
        isWarning
          ? 'border-amber-500/30 bg-amber-500/10 text-amber-600'
          : 'border-red-500/30 bg-red-500/10 text-red-500'
      }`}
    >
      <div className="flex items-start gap-2">
        {isWarning ? (
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        ) : (
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <div className="whitespace-pre-wrap">{content}</div>
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs opacity-80 transition-opacity hover:opacity-100"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5" /> Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" /> Copy details
                </>
              )}
            </button>
            {isWarning && (
              <button
                type="button"
                onClick={() => setDismissed(true)}
                className="flex items-center gap-1 text-xs opacity-80 transition-opacity hover:opacity-100"
              >
                <X className="h-3.5 w-3.5" /> Dismiss
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
