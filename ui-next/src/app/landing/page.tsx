'use client';

import { useAppStore } from '@/stores/app-store';
import { useRouter } from 'next/navigation';
import { ArrowRight, Brain, Zap, Shield, Database, Code, Globe } from 'lucide-react';
import Link from 'next/link';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function LandingPage() {
  const user = useAppStore((s) => s.user);
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex flex-col">
      <SiteHeader />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="px-4 py-24 text-center lg:py-32">
          <h1 className="mx-auto max-w-4xl text-5xl font-extrabold tracking-tight sm:text-7xl">
            Reasoning <span className="text-[var(--accent)]">Evolved</span>.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-[var(--text-muted)] sm:text-xl">
            Advanced Reasoning Architecture (Reasoner) breaks down complex problems, searches the web, tests multiple perspectives, and synthesizes perfect answers.
          </p>
          <div className="mt-10 flex justify-center gap-4">
            <button
              onClick={() => router.push(user ? '/chat' : '/signup')}
              className="flex items-center gap-2 rounded-full bg-[var(--text)] px-8 py-3.5 text-sm font-bold text-[var(--bg)] transition-transform hover:scale-105"
            >
              Start Reasoning <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => router.push('/about')}
              className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-8 py-3.5 text-sm font-bold transition-colors hover:bg-[var(--surface-2)]"
            >
              Learn More
            </button>
          </div>
        </section>

        {/* Features Section */}
        <section className="bg-[var(--surface)] px-4 py-24 lg:px-12">
          <div className="mx-auto max-w-6xl">
            <h2 className="mb-16 text-center text-3xl font-bold">Why ARA is different</h2>
            <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { icon: <Zap />, title: "Multi-Model Routing", desc: "Automatically selects the best model for each sub-task based on cost and capability." },
                { icon: <Shield />, title: "Fact Verification", desc: "Every answer is subjected to rigorous critique and fact-checking before final synthesis." },
                { icon: <Database />, title: "Neuro Memory", desc: "Learns from your previous interactions to provide rich, personalized context over time." },
                { icon: <Code />, title: "Dev-Ready", desc: "Built for engineers. Upload code, analyze architectural diagrams, and generate unit tests." },
                { icon: <Globe />, title: "Iterative RAG", desc: "Intelligently browses the web, refining its search queries until it finds the exact information needed." },
                { icon: <Brain />, title: "Perspective Debate", desc: "Simulates a jury of specialized AI agents debating different approaches to solve your problem." },
              ].map((f, i) => (
                <div key={i} className="flex flex-col rounded-2xl border border-[var(--border)] p-6 transition-colors hover:bg-[var(--surface-2)]">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--accent)]/10 text-[var(--accent)]">
                    {f.icon}
                  </div>
                  <h3 className="mb-2 text-lg font-bold">{f.title}</h3>
                  <p className="text-sm text-[var(--text-muted)]">{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
