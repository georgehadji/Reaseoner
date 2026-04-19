import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Conversation } from '@/lib/types';

export type Tier = 'budget' | 'premium';

interface AppState {
  running: boolean;
  tier: Tier;
  isSequential: boolean;
  isExpert: boolean;
  isWebSearch: boolean;
  isSmartSearch: boolean;
  isEnhancePrompt: boolean;
  sidebarCollapsed: boolean;
  composerText: string;
  history: Conversation[];
  activeRun: {
    progressId: string;
    problem: string;
    phases: Array<{ phase: number; name: string; data: unknown }>;
    errors: string[];
    preset: string;
    autoSelectedMethod: string | null;
  } | null;

  // Actions
  setRunning: (running: boolean) => void;
  toggleTier: () => void;
  toggleSequential: () => void;
  toggleExpert: () => void;
  toggleWebSearch: () => void;
  toggleSmartSearch: () => void;
  toggleEnhancePrompt: () => void;
  toggleSidebar: () => void;
  setComposerText: (text: string) => void;
  setHistory: (history: Conversation[]) => void;
  setActiveRun: (run: AppState['activeRun']) => void;
  addPhaseToActiveRun: (phase: { phase: number; name: string; data: unknown }) => void;
  setActiveRunErrors: (errors: string[]) => void;
  clearActiveRun: () => void;
  getAutoPreset: () => string;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      running: false,
      tier: 'budget',
      isSequential: false,
      isExpert: false,
      isWebSearch: false,
      isSmartSearch: true,
      isEnhancePrompt: true,
      sidebarCollapsed: false,
      composerText: '',
      history: [],
      activeRun: null,

      setRunning: (running) => set({ running }),

      toggleTier: () =>
        set((state) => ({ tier: state.tier === 'budget' ? 'premium' : 'budget' })),

      toggleSequential: () => set((state) => ({ isSequential: !state.isSequential })),
      toggleExpert: () => set((state) => ({ isExpert: !state.isExpert })),
      toggleWebSearch: () => set((state) => ({ isWebSearch: !state.isWebSearch, isSmartSearch: state.isWebSearch ? false : true })),
      toggleSmartSearch: () => set((state) => ({ isSmartSearch: !state.isSmartSearch })),
      toggleEnhancePrompt: () => set((state) => ({ isEnhancePrompt: !state.isEnhancePrompt })),
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

      /** Returns the preset string to send to the API: "auto-budget" or "auto-premium". */
      getAutoPreset: () => `auto-${get().tier}`,
    }),
    {
      name: 'ara-ui-store',
      version: 2,
      migrate: () => ({}),   // reset all persisted state on version bump
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        tier: state.tier,
        isSequential: state.isSequential,
        isExpert: state.isExpert,
        isEnhancePrompt: state.isEnhancePrompt,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);
