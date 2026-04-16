'use client';

import { useEffect } from 'react';
import { useAppStore } from '@/stores/app-store';
import { loadAllConversations, saveConversation as dbSaveConversation, deleteConversation as dbDeleteConversation, clearAllConversations as dbClearAllConversations } from '@/lib/db';
import { Conversation } from '@/lib/types';

export function useConversationHistory() {
  const history = useAppStore((s) => s.history);
  const setHistory = useAppStore((s) => s.setHistory);

  useEffect(() => {
    loadAllConversations().then(setHistory).catch(console.error);
  }, [setHistory]);

  const refresh = async () => {
    const conversations = await loadAllConversations();
    setHistory(conversations);
  };

  const save = async (conversation: Conversation) => {
    await dbSaveConversation(conversation);
    await refresh();
  };

  const remove = async (id: string) => {
    await dbDeleteConversation(id);
    await refresh();
  };

  const clear = async () => {
    await dbClearAllConversations();
    await refresh();
  };

  return { history, refresh, save, remove, clear };
}
