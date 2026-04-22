'use client';

const DEFAULT_FEATURES: Record<string, boolean> = {
  'cost-transparency': true,
  'typed-errors': true,
  'retry-ui': true,
  'compact-phases': true,
  'sources-panel': true,
  'drag-drop': true,
  'memory-badge': true,
  'command-palette': true,
  'keyboard-shortcuts': true,
  'feedback-loop': true,
  'continue-generating': true,
  'theme-transition': true,
};

const STORAGE_KEY = 'ara-feature-flags';

function loadFlags(): Record<string, boolean> {
  if (typeof window === 'undefined') return DEFAULT_FEATURES;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_FEATURES;
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return { ...DEFAULT_FEATURES, ...parsed };
  } catch {
    return DEFAULT_FEATURES;
  }
}

export function isEnabled(name: string): boolean {
  return loadFlags()[name] ?? DEFAULT_FEATURES[name] ?? false;
}

export function setEnabled(name: string, value: boolean): void {
  if (typeof window === 'undefined') return;
  const flags = loadFlags();
  flags[name] = value;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
}

export function resetFlags(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
}
