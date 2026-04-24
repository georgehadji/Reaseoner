'use client';

import { useMemo, useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { Conversation } from '@/lib/types';
import { Plus, PanelLeft, Trash2, Brain, History, Play } from 'lucide-react';
import { NeuroPanel } from './NeuroPanel';
import { Tooltip } from '@/components/ui/Tooltip';

interface SidebarProps {
  conversations: Conversation[];
  onLoad: (conv: Conversation) => void;
  onDelete: (id: string) => void;
  onClear: () => void;
  onNew: () => void;
  onResume?: (pipelineId: string) => void;
  /** Current conversation ID for Neuro tenant isolation */
  conversationId?: string | null;
  /** Last user prompt for manual Neuro Learn */
  lastUserPrompt?: string;
  /** Last assistant response for manual Neuro Learn */
  lastAssistantResponse?: string;
}

function formatDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const isSameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);

  const startOfWeek = new Date(now);
  startOfWeek.setDate(now.getDate() - now.getDay());

  if (isSameDay(date, now)) return 'Today';
  if (isSameDay(date, yesterday)) return 'Yesterday';
  if (date >= startOfWeek) return 'Earlier this week';
  return 'Older';
}

function MemoryStatus() {
  const [status, setStatus] = useState<'ok' | 'degraded' | 'unknown'>('unknown');

  useMemo(() => {
    fetch('/api/neuro/health')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => setStatus(d.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => setStatus('unknown'));
  }, []);

  return (
    <div className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-[var(--text-muted)]">
      <Brain className="h-3.5 w-3.5" />
      <span>Memory</span>
      <Tooltip text={status === 'ok' ? 'Healthy' : status === 'degraded' ? 'Degraded' : 'Unavailable'}>
        <span
          className={`ml-auto h-2 w-2 rounded-full ${
            status === 'ok'
              ? 'bg-green-500'
              : status === 'degraded'
              ? 'bg-amber-500'
              : 'bg-gray-400'
          }`}
        />
      </Tooltip>
    </div>
  );
}

export function Sidebar({ conversations, onLoad, onDelete, onClear, onNew, onResume, conversationId, lastUserPrompt, lastAssistantResponse }: SidebarProps) {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const neuroPanelOpen = useAppStore((s) => s.neuroPanelOpen);
  const toggleNeuroPanel = useAppStore((s) => s.toggleNeuroPanel);
  const [query, setQuery] = useState('');
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const methodTags = useMemo(
    () => Array.from(new Set(conversations.map((c) => c.method).filter(Boolean))),
    [conversations]
  );
  const presetTags = useMemo(
    () => Array.from(new Set(conversations.map((c) => c.preset).filter(Boolean))),
    [conversations]
  );

  const filtered = useMemo(() => {
    // Deduplicate by conversation_id, keeping the latest turn
    const latestByThread = new Map<string, Conversation>();
    conversations.forEach((c) => {
      const key = c.conversation_id || c.id;
      const existing = latestByThread.get(key);
      if (!existing || new Date(c.timestamp).getTime() > new Date(existing.timestamp).getTime()) {
        latestByThread.set(key, c);
      }
    });
    const list = Array.from(latestByThread.values());
    return list.filter((c) => {
      const matchesQuery =
        !query.trim() || c.problem.toLowerCase().includes(query.toLowerCase());
      const matchesTag = !activeTag || c.method === activeTag || c.preset === activeTag;
      return matchesQuery && matchesTag;
    });
  }, [conversations, query, activeTag]);

  const grouped = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    filtered.forEach((c) => {
      const group = formatDateGroup(c.timestamp);
      if (!map.has(group)) map.set(group, []);
      map.get(group)!.push(c);
    });
    const order = ['Today', 'Yesterday', 'Earlier this week', 'Older'];
    return order
      .filter((g) => map.has(g))
      .map((g) => ({ group: g, items: map.get(g)! }));
  }, [filtered]);

  return (
    <>
      {/* Mobile / collapse toggle overlay */}
      {!collapsed && (
        <div
          className="fixed inset-0 z-[40] bg-black/40 sm:hidden"
          onClick={toggleSidebar}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed left-0 top-0 z-[50] flex h-full flex-col border-r border-[var(--border)] bg-[var(--surface)] transition-[width] duration-200 sm:static ${
          collapsed ? 'w-0 overflow-hidden' : 'w-[260px]'
        }`}
      >
        <div className="flex items-center justify-between px-3 py-3">
          <button
            type="button"
            onClick={onNew}
            className="flex h-9 flex-1 items-center justify-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 text-sm font-medium text-[var(--text)] transition-colors hover:bg-[var(--surface-3)]"
          >
            <Plus className="h-4 w-4" />
            <span>New problem</span>
          </button>
          <button
            type="button"
            onClick={toggleSidebar}
            className="ml-2 flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            aria-label="Toggle sidebar"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        </div>

        <div className="mx-3 h-px bg-[var(--border)]" />

        <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-3">
          {/* Tab switcher */}
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => neuroPanelOpen && toggleNeuroPanel()}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                !neuroPanelOpen
                  ? 'bg-[var(--surface-2)] text-[var(--text)]'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-2)]'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              History
            </button>
            <button
              type="button"
              onClick={() => !neuroPanelOpen && toggleNeuroPanel()}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                neuroPanelOpen
                  ? 'bg-[var(--surface-2)] text-[var(--text)]'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-2)]'
              }`}
            >
              <Brain className="h-3.5 w-3.5" />
              Memory
            </button>
          </div>

          {neuroPanelOpen ? (
            <NeuroPanel
              conversationId={conversationId}
              lastUserPrompt={lastUserPrompt}
              lastAssistantResponse={lastAssistantResponse}
            />
          ) : (
            <>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search conversations"
                className="h-9 rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none"
              />

              {(methodTags.length > 0 || presetTags.length > 0) && (
                <div className="flex flex-wrap gap-1">
                  {activeTag && (
                    <button
                      type="button"
                      onClick={() => setActiveTag(null)}
                      className="rounded-full border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 text-xs text-[var(--text-muted)] hover:text-[var(--text)]"
                    >
                      Clear
                    </button>
                  )}
                  {methodTags.slice(0, 4).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => setActiveTag(tag === activeTag ? null : tag)}
                      className={`rounded-full px-2 py-0.5 text-xs transition-colors ${
                        activeTag === tag
                          ? 'bg-[var(--accent)] text-[var(--accent-text)]'
                          : 'border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)] hover:text-[var(--text)]'
                      }`}
                    >
                      {String(tag)}
                    </button>
                  ))}
                  {presetTags.slice(0, 4).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => setActiveTag(tag === activeTag ? null : tag)}
                      className={`rounded-full px-2 py-0.5 text-xs transition-colors ${
                        activeTag === tag
                          ? 'bg-[var(--accent)] text-[var(--accent-text)]'
                          : 'border border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-muted)] hover:text-[var(--text)]'
                      }`}
                    >
                      {String(tag)}
                    </button>
                  ))}
                </div>
              )}

              {filtered.length === 0 && (
                <div className="py-4 text-sm text-[var(--text-muted)]">No history yet</div>
              )}

              <div className="flex flex-col gap-4">
                {grouped.map(({ group, items }) => (
                  <div key={group} className="flex flex-col gap-1">
                    <div className="px-2 text-xs font-medium text-[var(--text-subtle)]">
                      {group}
                    </div>
                    {items.map((conv) => {
                      const title =
                        conv.problem.length > 45 ? conv.problem.slice(0, 45) + '…' : conv.problem;
                      const tokens = conv.total_tokens?.total ?? 0;

                      return (
                        <div
                          key={conv.id}
                          className="group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 transition-colors hover:bg-[var(--surface-2)]"
                          onClick={() => onLoad(conv)}
                        >
                          <div className="min-w-0 flex-1">
                            <Tooltip text={conv.problem}>
                              <div className="truncate text-sm text-[var(--text-2)]">
                                {title}
                              </div>
                            </Tooltip>
                            <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                              {conv.method && conv.method !== 'multi_perspective' && (
                                <span className="text-[10px] text-[var(--text-muted)]">
                                  {conv.method.replace(/_/g, '-')}
                                </span>
                              )}
                              {conv.preset && (
                                <span className="rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-subtle)]">
                                  {conv.preset}
                                </span>
                              )}
                              {tokens > 0 && (
                                <span className="text-[10px] text-[var(--text-subtle)]">
                                  {tokens.toLocaleString()} tokens
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            {onResume && conv.pipeline_id && conv.kind === 'pipeline' && (
                              <Tooltip text="Resume pipeline">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onResume(conv.pipeline_id!);
                                  }}
                                  className="rounded p-1 text-[var(--text-muted)] opacity-0 transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--accent)] group-hover:opacity-100"
                                  aria-label="Resume pipeline"
                                >
                                  <Play className="h-3.5 w-3.5" />
                                </button>
                              </Tooltip>
                            )}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onDelete(conv.id);
                              }}
                              className="rounded p-1 text-[var(--text-muted)] opacity-0 transition-colors hover:bg-[var(--surface-3)] hover:text-red-500 group-hover:opacity-100"
                              aria-label="Delete conversation"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="border-t border-[var(--border)] p-3">
          <MemoryStatus />
          <button
            type="button"
            onClick={onClear}
            className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
          >
            Clear cache
          </button>
        </div>
      </aside>

      {/* Collapsed state floating toggle (visible only when fully collapsed on desktop) */}
      {collapsed && (
        <button
          type="button"
          onClick={toggleSidebar}
          className="fixed left-3 top-3 z-[50] hidden h-9 w-9 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)] sm:flex"
          aria-label="Open sidebar"
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      )}
    </>
  );
}
