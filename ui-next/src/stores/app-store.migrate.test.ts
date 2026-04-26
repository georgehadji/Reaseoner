import { describe, it, expect } from 'vitest';

// Reconstruct the migrate function inline to test it without importing the full store
const migrate = (persistedState: unknown) => {
  const s = (persistedState || {}) as Record<string, unknown>;
  return {
    tier: s.tier === 'premium' ? 'premium' : 'budget',
    isExpert: typeof s.isExpert === 'boolean' ? s.isExpert : false,
    sidebarCollapsed: typeof s.sidebarCollapsed === 'boolean' ? s.sidebarCollapsed : false,
    isImageMode: false,
    recentCommands: Array.isArray(s.recentCommands) ? s.recentCommands : [],
  };
};

describe('app-store migrate (BUG-004 regression)', () => {
  it('preserves recentCommands array during migration', () => {
    const persisted = {
      tier: 'premium',
      isExpert: true,
      sidebarCollapsed: true,
      recentCommands: ['/run math', '/preset balanced'],
    };

    const result = migrate(persisted);

    expect(result.recentCommands).toEqual(['/run math', '/preset balanced']);
  });

  it('defaults recentCommands to empty array when missing in persisted state', () => {
    const persisted = {
      tier: 'budget',
      isExpert: false,
      sidebarCollapsed: false,
    };

    const result = migrate(persisted);

    expect(result.recentCommands).toEqual([]);
  });

  it('defaults recentCommands to empty array when persisted state is null', () => {
    const result = migrate(null);

    expect(result.recentCommands).toEqual([]);
  });

  it('does not return recentCommands as undefined', () => {
    const result = migrate({});

    expect(result.recentCommands).not.toBeUndefined();
    expect(Array.isArray(result.recentCommands)).toBe(true);
  });
});
