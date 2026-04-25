'use client';

import { STORAGE_KEYS } from '@/lib/config';

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

const STORAGE_KEY = STORAGE_KEYS.featureFlags;

let _cachedFlags: Record<string, boolean> | null = null;
let _storageListenerAdded = false;

function _addStorageListener(): void {
  if (_storageListenerAdded || typeof window === 'undefined') return;
  _storageListenerAdded = true;
  window.addEventListener('storage', (e) => {
    if (e.key === STORAGE_KEY) {
      _cachedFlags = null;
    }
  });
}

function loadFlags(): Record<string, boolean> {
  if (typeof window === 'undefined') return DEFAULT_FEATURES;
  _addStorageListener();
  if (_cachedFlags) return _cachedFlags;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      _cachedFlags = DEFAULT_FEATURES;
      return _cachedFlags;
    }
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    _cachedFlags = { ...DEFAULT_FEATURES, ...parsed };
    return _cachedFlags;
  } catch {
    _cachedFlags = DEFAULT_FEATURES;
    return _cachedFlags;
  }
}

export function isEnabled(name: string): boolean {
  return loadFlags()[name] ?? DEFAULT_FEATURES[name] ?? false;
}

export function setEnabled(name: string, value: boolean): void {
  if (typeof window === 'undefined') return;
  const flags = loadFlags();
  flags[name] = value;
  _cachedFlags = { ...flags };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
}

export function resetFlags(): void {
  if (typeof window === 'undefined') return;
  _cachedFlags = null;
  localStorage.removeItem(STORAGE_KEY);
}
