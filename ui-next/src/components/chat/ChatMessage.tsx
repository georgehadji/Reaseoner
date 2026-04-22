'use client';

import { memo } from 'react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  children: React.ReactNode;
}

const ChatMessageComponent = ({ role, children }: ChatMessageProps) => {
  const isUser = role === 'user';

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`w-full max-w-3xl ${
          isUser
            ? 'rounded-3xl rounded-br-md bg-[var(--accent)] px-5 py-3 text-[var(--accent-text)]'
            : 'text-[var(--text)] text-[18px] leading-relaxed break-words'
        } ${isUser ? '' : 'mx-auto'}`}
      >
        {isUser ? <div className="whitespace-pre-wrap text-[15px] leading-relaxed">{children}</div> : <>{children}</>}
      </div>
    </div>
  );
};

export const ChatMessage = memo(ChatMessageComponent);

import { TIMING } from '@/lib/config';

export function StreamingIndicator() {
  return (
    <div className="flex w-full justify-start">
      <div className="flex items-center gap-1 rounded-2xl bg-[var(--surface)] px-4 py-3">
        {TIMING.streamingBounceDelays.map((delay) => (
          <span
            key={delay}
            className="h-2 w-2 animate-bounce rounded-full bg-[var(--text-muted)]"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
    </div>
  );
}
