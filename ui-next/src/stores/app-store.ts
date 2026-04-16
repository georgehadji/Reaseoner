import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { MethodId, Conversation } from '@/lib/types';
import { METHOD_PRESETS, DEFAULTS } from '@/lib/config';

interface AppState {
  running: boolean;
  method: MethodId;
  presetIndex: number;
  isSequential: boolean;
  isExpert: boolean;
  isWebSearch: boolean;
  isSmartSearch: boolean;
  sidebarCollapsed: boolean;
  composerText: string;
  history: Conversation[];
  activeRun: {
    progressId: string;
    problem: string;
    phases: Array<{ phase: number; name: string; data: unknown }>;
    errors: string[];
    preset: string;
    method: MethodId;
  } | null;

  // Actions
  setRunning: (running: boolean) => void;
  setMethod: (method: MethodId) => void;
  cyclePreset: () => void;
  toggleSequential: () => void;
  toggleExpert: () => void;
  toggleWebSearch: () => void;
  toggleSmartSearch: () => void;
  toggleSidebar: () => void;
  setComposerText: (text: string) => void;
  setHistory: (history: Conversation[]) => void;
  setActiveRun: (run: AppState['activeRun']) => void;
  addPhaseToActiveRun: (phase: { phase: number; name: string; data: unknown }) => void;
  setActiveRunErrors: (errors: string[]) => void;
  clearActiveRun: () => void;
  getCurrentPreset: () => string;
  getCurrentPresetLabel: () => string;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      running: false,
      method: DEFAULTS.method,
      presetIndex: 0,
      isSequential: false,
      isExpert: false,
      isWebSearch: false,
      isSmartSearch: false,
      sidebarCollapsed: false,
      composerText: '',
      history: [],
      activeRun: null,

      setRunning: (running) => set({ running }),

      setMethod: (method) =>
        set((state) => {
          const presets = METHOD_PRESETS[method] || METHOD_PRESETS[DEFAULTS.method];
          const presetIndex = state.presetIndex >= presets.length ? 0 : state.presetIndex;
          return { method, presetIndex };
        }),

      cyclePreset: () =>
        set((state) => {
          const presets = METHOD_PRESETS[state.method] || METHOD_PRESETS[DEFAULTS.method];
          const presetIndex = (state.presetIndex + 1) % presets.length;
          return { presetIndex };
        }),

      toggleSequential: () => set((state) => ({ isSequential: !state.isSequential })),
      toggleExpert: () => set((state) => ({ isExpert: !state.isExpert })),
      toggleWebSearch: () => set((state) => ({ isWebSearch: !state.isWebSearch, isSmartSearch: false })),
      toggleSmartSearch: () => set((state) => ({ isSmartSearch: !state.isSmartSearch })),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setComposerText: (composerText) => set({ composerText }),
      setHistory: (history) => set({ history }),
      setActiveRun: (activeRun) => set({ activeRun }),

      addPhaseToActiveRun: (phase) =>
        set((state) => {
          if (!state.activeRun) return state;
          return {
            activeRun: {
              ...state.activeRun,
              phases: [...state.activeRun.phases, phase],
            },
          };
        }),

      setActiveRunErrors: (errors) =>
        set((state) => {
          if (!state.activeRun) return state;
          return { activeRun: { ...state.activeRun, errors } };
        }),

      clearActiveRun: () => set({ activeRun: null }),

      getCurrentPreset: () => {
        const presets = METHOD_PRESETS[get().method] || METHOD_PRESETS[DEFAULTS.method];
        const idx = Math.min(get().presetIndex, presets.length - 1);
        return presets[idx]?.id || presets[0]?.id;
      },

      getCurrentPresetLabel: () => {
        const presets = METHOD_PRESETS[get().method] || METHOD_PRESETS[DEFAULTS.method];
        const idx = Math.min(get().presetIndex, presets.length - 1);
        return presets[idx]?.label || presets[0]?.label;
      },
    }),
    {
      name: 'ara-ui-store',
      version: 1,
      migrate: (persistedState) => {
        // Drop persisted method so it always defaults to multi-perspective
        const s = persistedState as Record<string, unknown>;
        const { method: _, ...rest } = s;
        return rest;
      },
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        presetIndex: state.presetIndex,
        isSequential: state.isSequential,
        isExpert: state.isExpert,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
