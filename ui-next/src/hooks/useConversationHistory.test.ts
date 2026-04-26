// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

let resolveLoad: ((value: { items: unknown[]; nextCursor: string | null }) => void) | null = null;

vi.mock('@/lib/db', () => ({
  loadConversationsPage: vi.fn(() => new Promise((res) => { resolveLoad = res; })),
  saveConversation: vi.fn(),
  deleteConversation: vi.fn(),
  clearAllConversations: vi.fn(),
}));

import { loadConversationsPage } from '@/lib/db';
import { useConversationHistory } from './useConversationHistory';

describe('useConversationHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resolveLoad = null;
  });

  it('does not update state after unmount (BUG-007 regression)', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { unmount } = renderHook(() => useConversationHistory());

    // Unmount before the promise resolves
    unmount();

    // Now resolve the delayed promise
    if (resolveLoad) {
      resolveLoad({ items: [{ id: '1' }], nextCursor: null });
    }

    // Wait a tick for any microtasks
    await waitFor(() => expect(loadConversationsPage).toHaveBeenCalledTimes(1));

    // React should not warn about state updates on unmounted component
    const reactWarnings = consoleErrorSpy.mock.calls.filter(
      ([msg]) => typeof msg === 'string' && msg.includes("Can't perform a React state update")
    );
    expect(reactWarnings).toHaveLength(0);

    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });
});
