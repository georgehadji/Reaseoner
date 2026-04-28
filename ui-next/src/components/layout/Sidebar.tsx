'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAppStore } from '@/stores/app-store';
import { Conversation } from '@/lib/types';
import { Plus, PanelLeft, Trash2, Brain, History, Play, Search } from 'lucide-react';
import { NeuroPanel } from './NeuroPanel';
import { Tooltip } from '@/components/ui/Tooltip';
import { API, LIMITS, PIPELINE_DEFAULTS } from '@/lib/config';
import { cn } from '@/lib/utils';

interface SidebarProps {
  conversations: Conversation[];
  onLoad: (conv: Conversation) => void;
  onDelete: (id: string) => void;
  onClear: () => void;
  onNew: () => void;
  onResume?: (pipelineId: string) => void;
  conversationId?: string | null;
  lastUserPrompt?: string;
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
  if (date >= startOfWeek) return 'This week';
  return 'Older';
}

function MemoryStatus() {
  const [status, setStatus] = useState<'ok' | 'degraded' | 'unknown'>('unknown');
  useEffect(() => {
    let mounted = true;
    fetch(API.NEURO_HEALTH)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => { if (mounted) setStatus(d.status === 'ok' ? 'ok' : 'degraded'); })
      .catch(() => { if (mounted) setStatus('unknown'); });
    return () => { mounted = false; };
  }, []);

  const dotColor =
    status === 'ok' ? 'bg-[#808080]' :
    status === 'degraded' ? 'bg-[#A0A0A0]' :
    'bg-[var(--text-subtle)]';

  return (
    <Tooltip text={status === 'ok' ? 'Memory healthy' : status === 'degraded' ? 'Memory degraded' : 'Memory unavailable'}>
      <div className="flex cursor-default items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-[var(--text-muted)]">
        <Brain className="h-3.5 w-3.5" />
        <span>Memory</span>
        <span className={cn('ml-auto h-1.5 w-1.5 rounded-full', dotColor)} />
      </div>
    </Tooltip>
  );
}

export function Sidebar({
  conversations,
  onLoad,
  onDelete,
  onClear,
  onNew,
  onResume,
  conversationId,
  lastUserPrompt,
  lastAssistantResponse,
}: SidebarProps) {
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const neuroPanelOpen = useAppStore((s) => s.neuroPanelOpen);
  const toggleNeuroPanel = useAppStore((s) => s.toggleNeuroPanel);
  const [query, setQuery] = useState('');
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const methodTags = useMemo(
    () => Array.from(new Set(conversations.map((c) => c.method).filter(Boolean))),
    [conversations],
  );

  const filtered = useMemo(() => {
    const latestByThread = new Map<string, Conversation>();
    conversations.forEach((c) => {
      const key = c.conversation_id || c.id;
      const existing = latestByThread.get(key);
      if (!existing || new Date(c.timestamp) > new Date(existing.timestamp)) {
        latestByThread.set(key, c);
      }
    });
    return Array.from(latestByThread.values()).filter((c) => {
      const matchesQuery = !query.trim() || c.problem.toLowerCase().includes(query.toLowerCase());
      const matchesTag = !activeTag || c.method === activeTag || c.preset === activeTag;
      return matchesQuery && matchesTag;
    });
  }, [conversations, query, activeTag]);

  const grouped = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    filtered.forEach((c) => {
      const g = formatDateGroup(c.timestamp);
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(c);
    });
    return ['Today', 'Yesterday', 'This week', 'Older']
      .filter((g) => map.has(g))
      .map((g) => ({ group: g, items: map.get(g)! }));
  }, [filtered]);

  return (
    <>
      {/* Mobile backdrop */}
      {!collapsed && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm sm:hidden"
          onClick={toggleSidebar}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-full flex-col border-r border-[var(--border)] bg-[var(--surface)] transition-[width] duration-500 ease-[var(--ease-out-expo)] sm:static',
          collapsed ? 'w-0 overflow-hidden' : 'w-[264px]',
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 pt-3 pb-2">
          <button
            type="button"
            onClick={onNew}
            className="flex h-10 flex-1 cursor-pointer items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-3 text-sm font-medium text-[var(--text)] transition-all hover:border-[var(--border-strong)] hover:bg-[var(--surface-3)]"
          >
            <Plus className="h-3.5 w-3.5 text-[var(--accent)]" />
            New problem
          </button>
          <Tooltip text="Collapse sidebar">
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex h-10 w-10 cursor-pointer items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
              aria-label="Collapse sidebar"
            >
              <PanelLeft className="h-4 w-4" />
            </button>
          </Tooltip>
        </div>

        {/* Tab switcher */}
        <div className="mx-3 flex gap-1 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] p-1">
          <button
            type="button"
            onClick={() => neuroPanelOpen && toggleNeuroPanel()}
            className={cn(
              'flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-2.5 text-xs font-medium transition-all',
              !neuroPanelOpen
                ? 'bg-[var(--surface)] text-[var(--text)] shadow-[var(--shadow)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text)]',
            )}
          >
            <History className="h-3.5 w-3.5" />
            History
          </button>
          <button
            type="button"
            onClick={() => !neuroPanelOpen && toggleNeuroPanel()}
            className={cn(
              'flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-2.5 text-xs font-medium transition-all',
              neuroPanelOpen
                ? 'bg-[var(--surface)] text-[var(--text)] shadow-[var(--shadow)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text)]',
            )}
          >
            <Brain className="h-3.5 w-3.5" />
            Memory
          </button>
        </div>

        <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-3 scrollbar-thin">
          {neuroPanelOpen ? (
            <NeuroPanel
              conversationId={conversationId}
              lastUserPrompt={lastUserPrompt}
              lastAssistantResponse={lastAssistantResponse}
            />
          ) : (
            <>
              {/* Search */}
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search conversations…"
                  className="h-9 w-full rounded-xl border border-[var(--border)] bg-[var(--surface-2)] pl-9 pr-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] transition-all duration-200 focus:border-[var(--border-strong)] focus:outline-none focus:shadow-[0_0_0_3px_rgba(59,130,246,0.10)]"
                />
              </div>

              {/* Method filter tags */}
              {methodTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {activeTag && (
                    <button
                      type="button"
                      onClick={() => setActiveTag(null)}
                      className="cursor-pointer rounded-full border border-[var(--border)] px-3 h-10 flex items-center text-xs text-[var(--text-muted)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text)]"
                    >
                      Clear ×
                    </button>
                  )}
                  {methodTags.slice(0, LIMITS.maxTagDisplay).map((tag) => (
                    <button
                      key={String(tag)}
                      type="button"
                      onClick={() => setActiveTag(tag === activeTag ? null : tag ?? null)}
                      className={cn(
                        'cursor-pointer rounded-full px-3 h-10 flex items-center text-xs font-medium transition-all',
                        activeTag === tag
                          ? 'bg-[var(--accent)] text-white'
                          : 'border border-[var(--border)] text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:text-[var(--text)]',
                      )}
                    >
                      {String(tag).replace(/_/g, '-')}
                    </button>
                  ))}
                </div>
              )}

              {/* Empty state */}
              {filtered.length === 0 && (
                <div className="flex flex-col items-center gap-2 py-12 text-center">
                  <History className="h-8 w-8 text-[var(--text-subtle)]" />
                  <p className="text-sm text-[var(--text-muted)]">No conversations yet</p>
                  <p className="text-xs text-[var(--text-subtle)]">Start reasoning to see history here</p>
                </div>
              )}

              {/* Grouped list */}
              <div className="flex flex-col gap-5">
                {grouped.map(({ group, items }) => (
                  <div key={group}>
                    <div className="mb-1.5 px-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-subtle)]">
                      {group}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      {items.map((conv) => {
                        const title =
                          conv.problem.length > LIMITS.titleTruncateChars
                            ? conv.problem.slice(0, LIMITS.titleTruncateChars) + '…'
                            : conv.problem;
                        return (
                          <div
                            key={conv.id}
                            role="button"
                            tabIndex={0}
                            className="group flex cursor-pointer items-start gap-2 rounded-xl px-2 py-2.5 transition-all duration-200 hover:bg-[var(--surface-2)] hover:translate-x-0.5"
                            onClick={() => onLoad(conv)}
                            onKeyDown={(e) => e.key === 'Enter' && onLoad(conv)}
                          >
                            <div className="min-w-0 flex-1">
                              <Tooltip text={conv.problem}>
                                <div className="truncate text-sm text-[var(--text-2)] leading-snug">
                                  {title}
                                </div>
                              </Tooltip>
                              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                                {conv.method && conv.method !== PIPELINE_DEFAULTS.method && (
                                  <span className="text-[10px] text-[var(--text-muted)]">
                                    {conv.method.replace(/_/g, '-')}
                                  </span>
                                )}
                                {conv.preset && (
                                  <span className="rounded border border-[var(--border)] px-1 text-[10px] text-[var(--text-subtle)]">
                                    {conv.preset}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                              {onResume && conv.pipeline_id && conv.kind === 'pipeline' && (
                                <Tooltip text="Resume">
                                  <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); onResume(conv.pipeline_id!); }}
                                    className="cursor-pointer flex h-10 w-10 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-[var(--accent)]"
                                    aria-label="Resume pipeline"
                                  >
                                    <Play className="h-4 w-4" />
                                  </button>
                                </Tooltip>
                              )}
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
                                className="cursor-pointer flex h-10 w-10 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-3)] hover:text-red-400"
                                aria-label="Delete"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[var(--border)] p-3">
          <MemoryStatus />
          <button
            type="button"
            onClick={onClear}
            className="mt-1 w-full min-h-[40px] cursor-pointer rounded-xl px-3 py-2 text-left text-xs text-[var(--text-subtle)] transition-colors hover:bg-[var(--surface-2)] hover:text-[var(--text-muted)]"
          >
            Clear cache
          </button>
        </div>
      </aside>

      {/* Floating toggle when collapsed */}
      {collapsed && (
        <Tooltip text="Open sidebar">
          <button
            type="button"
            onClick={toggleSidebar}
            className="fixed left-3 top-3 z-50 hidden h-10 w-10 cursor-pointer items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-muted)] shadow-[var(--shadow)] transition-all hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--text)] sm:flex"
            aria-label="Open sidebar"
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        </Tooltip>
      )}
    </>
  );
}
