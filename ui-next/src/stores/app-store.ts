import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Conversation } from '@/lib/types';

export interface ComposerAttachment {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  previewUrl?: string;
}

export type Tier = 'budget' | 'premium';

interface AppState {
  running: boolean;
  tier: Tier;
  isExpert: boolean;
  isImageMode: boolean;
  sidebarCollapsed: boolean;
  neuroPanelOpen: boolean;
  composerText: string;
  attachments: ComposerAttachment[];
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
  toggleExpert: () => void;
  toggleImageMode: () => void;
  toggleSidebar: () => void;
  toggleNeuroPanel: () => void;
  setComposerText: (text: string) => void;
  addAttachment: (file: File) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;
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
      isExpert: false,
      isImageMode: false,
      sidebarCollapsed: false,
      neuroPanelOpen: false,
      composerText: '',
      attachments: [],
      history: [],
      activeRun: null,

      setRunning: (running) => set({ running }),

      toggleTier: () =>
        set((state) => ({ tier: state.tier === 'budget' ? 'premium' : 'budget' })),

      toggleExpert: () => set((state) => ({ isExpert: !state.isExpert })),
      toggleImageMode: () => set((state) => ({ isImageMode: !state.isImageMode })),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      toggleNeuroPanel: () => set((state) => ({ neuroPanelOpen: !state.neuroPanelOpen })),
      setComposerText: (composerText) => set({ composerText }),

      addAttachment: (file) =>
        set((state) => {
          if (state.attachments.length >= 5) return state;
          const id = `att-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
          const attachment: ComposerAttachment = {
            id,
            file,
            name: file.name,
            size: file.size,
            type: file.type,
            previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
          };
          return { attachments: [...state.attachments, attachment] };
        }),

      removeAttachment: (id) =>
        set((state) => {
          const att = state.attachments.find((a) => a.id === id);
          if (att?.previewUrl) URL.revokeObjectURL(att.previewUrl);
          return { attachments: state.attachments.filter((a) => a.id !== id) };
        }),

      clearAttachments: () =>
        set((state) => {
          state.attachments.forEach((a) => {
            if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);
          });
          return { attachments: [] };
        }),
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
      migrate: (persistedState) => {
        const s = (persistedState || {}) as Record<string, unknown>;
        return {
          tier: s.tier === 'premium' ? 'premium' : 'budget',
          isExpert: typeof s.isExpert === 'boolean' ? s.isExpert : false,
          sidebarCollapsed: typeof s.sidebarCollapsed === 'boolean' ? s.sidebarCollapsed : false,
          // Force image mode false on migration/load
          isImageMode: false,
        };
      },
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        tier: state.tier,
        isExpert: state.isExpert,
        sidebarCollapsed: state.sidebarCollapsed,
        // Do not persist isImageMode so it defaults to false on next load
      }),
    }
  )
);
