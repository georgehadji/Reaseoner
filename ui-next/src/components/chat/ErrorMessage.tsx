'use client';

import { useState, useMemo } from 'react';
import { X, Copy, Check, AlertTriangle, AlertCircle, RotateCcw, Pencil } from 'lucide-react';
import { TIMING } from '@/lib/config';
import { copyToClipboard } from '@/lib/utils';
import { isEnabled } from '@/hooks/useFeatureFlags';

interface ErrorMessageProps {
  content: string;
  errorType?: string | null;
  retryable?: boolean | null;
  onRetry?: () => void;
  onEditRetry?: () => void;
}

function isWarningContent(content: string): boolean {
  return /warning|citation integrity|vetting flags|skipped|ignored/i.test(content);
}

/** Parses JSON-like error messages to extract a user-friendly string. */
function parseErrorMessage(content: string): { display: string; original: string } {
  try {
    const parsed = JSON.parse(content);
    if (parsed && typeof parsed === 'object') {
      if (parsed.error?.message) return { display: parsed.error.message, original: content };
      if (parsed.detail) return { display: parsed.detail, original: content };
      // Fallback for other common error structures, stringify for display if object
      return { display: JSON.stringify(parsed, null, 2), original: content };
    }
  } catch (e) {
    // Not JSON, or malformed JSON. Continue to other checks.
  }

  // Detect and parse Python tracebacks
  if (content.includes('Traceback (most recent call last):')) {
    const lines = content.split('\n');
    // Find the last line that looks like an error message
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (line && !line.startsWith('File') && !line.startsWith('  ')) {
        return { display: line, original: content }; // e.g., "AttributeError: 'NoneType' object has no attribute 'foo'"
      }
    }
    return { display: 'An internal server error occurred. Check details for traceback.', original: content };
  }

  // Detect other common Python errors not necessarily with a full traceback header
  if (content.includes('AttributeError:') || content.includes('TypeError:') || content.includes('ValueError:') || content.includes('KeyError:')) {
    const firstErrorLine = content.split('\n').find(line => line.includes('Error:'));
    if (firstErrorLine) {
      return { display: firstErrorLine.trim(), original: content };
    }
    return { display: 'An internal Python error occurred. Check details for more info.', original: content };
  }


  return { display: content, original: content };
}

export function ErrorMessage({ content, errorType, retryable, onRetry, onEditRetry }: ErrorMessageProps) {
  const [dismissed, setDismissed] = useState(false);
  const [copied, setCopied] = useState(false);
  const { display, original } = useMemo(() => parseErrorMessage(content), [content]);
  const isWarning = isWarningContent(original); // Check original content for warning patterns
  const showRetry = isEnabled('retry-ui') && retryable && onRetry;
  const showEditRetry = isEnabled('retry-ui') && onEditRetry;

  async function handleCopy() {
    const ok = await copyToClipboard(original);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), TIMING.copiedFeedbackMs);
    }
  }

  if (dismissed) return null;

  return (
    <div
      className={`max-w-[85%] rounded-[8px] border px-4 py-3 font-systemUi text-body sm:max-w-[75%] ${
        isWarning
          ? 'border-mds-color-vault-button-background/[0.3] bg-mds-color-vault-button-background/[0.1] text-mds-color-hcp-brand'
          : 'border-mds-color-unified-core-red-7/[0.3] bg-mds-color-unified-core-red-7/[0.1] text-mds-color-unified-core-red-7'
      }`}
    >
      <div className="flex items-start gap-2">
        {isWarning ? (
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-mds-color-vault-button-background" />
        ) : (
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-mds-color-unified-core-red-7" />
        )}
        <div className="min-w-0 flex-1">
          <div className="whitespace-pre-wrap font-systemUi text-body text-mds-color-hcp-brand">{display}</div>
          <div className="mt-2 flex flex-wrap items-center gap-3 font-systemUi text-caption text-mds-color-dark-gray">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 opacity-80 transition-opacity hover:opacity-100 hover:text-mds-color-near-white"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-mds-color-bright-blue" /> Copied!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" /> Copy details
                </>
              )}
            </button>
            {showRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="flex items-center gap-1 opacity-80 transition-opacity hover:opacity-100 hover:text-mds-color-near-white"
              >
                <RotateCcw className="h-3.5 w-3.5" /> Retry
              </button>
            )}
            {showEditRetry && (
              <button
                type="button"
                onClick={onEditRetry}
                className="flex items-center gap-1 opacity-80 transition-opacity hover:opacity-100 hover:text-mds-color-near-white"
              >
                <Pencil className="h-3.5 w-3.5" /> Edit & Retry
              </button>
            )}
            {isWarning && (
              <button
                type="button"
                onClick={() => setDismissed(true)}
                className="flex items-center gap-1 opacity-80 transition-opacity hover:opacity-100 hover:text-mds-color-near-white"
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
