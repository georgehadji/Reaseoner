// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useServerStatus } from './useServerStatus';

describe('useServerStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Reset visibility to visible before each test
    Object.defineProperty(document, 'hidden', {
      writable: true,
      configurable: true,
      value: false,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('removes visibilitychange listener on unmount (BUG-001 regression)', () => {
    const addSpy = vi.spyOn(document, 'addEventListener');
    const removeSpy = vi.spyOn(document, 'removeEventListener');

    const { unmount } = renderHook(() => useServerStatus());

    // Should have added exactly one visibilitychange listener
    const visibilityCalls = addSpy.mock.calls.filter(
      ([type]) => type === 'visibilitychange'
    );
    expect(visibilityCalls).toHaveLength(1);

    unmount();

    // Should have removed exactly one visibilitychange listener
    const removalCalls = removeSpy.mock.calls.filter(
      ([type]) => type === 'visibilitychange'
    );
    expect(removalCalls).toHaveLength(1);

    // The removed handler must be the same function reference that was added
    const addedHandler = visibilityCalls[0][1] as EventListener;
    const removedHandler = removalCalls[0][1] as EventListener;
    expect(removedHandler).toBe(addedHandler);
  });

  it('does not leak intervals when visibility toggles rapidly (BUG-001 regression)', () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval');
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

    renderHook(() => useServerStatus());

    // Initial start() calls check() + setInterval
    expect(setIntervalSpy).toHaveBeenCalledTimes(1);

    // Toggle hidden → visible three times
    for (let i = 0; i < 3; i++) {
      Object.defineProperty(document, 'hidden', { value: true, writable: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));

      Object.defineProperty(document, 'hidden', { value: false, writable: true, configurable: true });
      document.dispatchEvent(new Event('visibilitychange'));
    }

    // setInterval should have been called once per visible toggle (plus initial),
    // but clearInterval should have been called the same number of times
    // because start() guards against duplicate intervals
    expect(setIntervalSpy.mock.calls.length).toBeLessThanOrEqual(4);
    expect(clearIntervalSpy.mock.calls.length).toBeGreaterThanOrEqual(3);
  });
});
