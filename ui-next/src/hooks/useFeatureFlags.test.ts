// @vitest-environment jsdom
import { describe, it, expect, beforeEach } from 'vitest';
import { isEnabled, setEnabled, resetFlags } from './useFeatureFlags';

describe('useFeatureFlags', () => {
  beforeEach(() => {
    resetFlags();
    localStorage.clear();
  });

  it('does not mutate DEFAULT_FEATURES when setEnabled is called (BUG-003 regression)', () => {
    // Before fix, calling setEnabled would mutate the module-level DEFAULT_FEATURES object
    const before = isEnabled('cost-transparency');
    expect(before).toBe(true);

    setEnabled('cost-transparency', false);

    // The specific flag should now be false
    expect(isEnabled('cost-transparency')).toBe(false);

    // Reset and re-check: DEFAULT_FEATURES must still have the original value
    resetFlags();
    expect(isEnabled('cost-transparency')).toBe(true);
  });

  it('persists feature flag changes to localStorage', () => {
    setEnabled('typed-errors', false);
    const stored = JSON.parse(localStorage.getItem('reasoner-feature-flags') || '{}');
    expect(stored['typed-errors']).toBe(false);
  });

  it('returns default value for unknown flags', () => {
    expect(isEnabled('nonexistent-flag')).toBe(false);
  });
});
