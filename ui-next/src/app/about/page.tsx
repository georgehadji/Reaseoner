'use client';

import { Brain, Cpu, Database, Network, ShieldCheck, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function AboutPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-4 py-12 flex-1 w-full">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-[var(--text)] sm:text-5xl">
          About <span className="text-[var(--accent)]">ARA</span>
        </h1>
        <p className="mt-4 text-lg text-[var(--text-muted)] max-w-2xl mx-auto">
          Advanced Reasoning Architecture. A multi-method AI system designed for complex questions, strategic decisions, and deep research tasks.
        </p>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <div className="flex gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 transition-shadow hover:shadow-[var(--shadow-lg)]">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]/10 text-[var(--accent)]">
            <Network className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[var(--text)]">Multi-Method Pipeline</h3>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Instead of one-shot completions, ARA breaks down problems using specialized phases: decomposition, RAG vetting, multi-perspective generation, and rigorous synthesis.
            </p>
          </div>
        </div>

        <div className="flex gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 transition-shadow hover:shadow-[var(--shadow-lg)]">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]/10 text-[var(--accent)]">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[var(--text)]">Provider Routing</h3>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Seamlessly routes sub-tasks to the best-in-class models (Anthropic, OpenAI, DeepSeek, Google, etc.) based on cost, speed, and capability.
            </p>
          </div>
        </div>

        <div className="flex gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 transition-shadow hover:shadow-[var(--shadow-lg)]">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]/10 text-[var(--accent)]">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[var(--text)]">Neuro Memory</h3>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              A sophisticated caching and embedding engine that learns from past interactions, providing rich context to future queries without overwhelming token limits.
            </p>
          </div>
        </div>

        <div className="flex gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 transition-shadow hover:shadow-[var(--shadow-lg)]">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]/10 text-[var(--accent)]">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[var(--text)]">Stress Testing</h3>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Candidate answers are subjected to rigorous critique, factual verification, and logical stress testing before being presented to the user.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-12 flex justify-center">
        <button
          onClick={() => router.push('/')}
          className="inline-flex items-center justify-center rounded-lg bg-[var(--accent)] px-6 py-3 text-sm font-medium text-[var(--accent-text)] transition-colors hover:opacity-90"
        >
          <Zap className="mr-2 h-4 w-4" />
          Start Reasoning
        </button>
      </div>
      </main>
      <SiteFooter />
    </div>
  );
}
