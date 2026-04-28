'use client';

import { useAppStore } from '@/stores/app-store';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';
import { NebulaBackground } from '@/components/layout/NebulaBackground';
import {
  ArrowRight,
  Zap,
  Shield,
  Database,
  Code,
  Globe,
  Brain,
  FlaskConical,
  Scale,
  Network,
  Search,
  BarChart3,
  Layers,
  GitMerge,
} from 'lucide-react';

/* ─── Data ─────────────────────────────────────────────── */

const METHODS = [
  'Multi-Perspective', 'Debate', 'Jury Consensus', 'Research RAG',
  'Scientific', 'Socratic', 'Pre-Mortem', 'Bayesian',
  'Dialectical', 'Analogical', 'Delphi', 'Chain-of-Verification',
  'Skeleton-of-Thought', 'Tree-of-Thoughts', 'Program-of-Thoughts',
  'Self-Discover', 'Writing',
];

const STATS = [
  { value: '90+', label: 'AI Models' },
  { value: '17', label: 'Reasoning Methods' },
  { value: '42', label: 'Presets' },
  { value: '6', label: 'Model Labs' },
];

const FEATURES = [
  {
    icon: Network,
    title: 'Multi-Model Routing',
    desc: 'Automatically selects the best model for each sub-task. Cross-lab diversity prevents echo chambers in every run.',
    accent: 'teal',
    size: 'tall',
  },
  {
    icon: Shield,
    title: 'Fact Verification',
    desc: 'Every answer passes rigorous critique and independent scoring before the final synthesis.',
    accent: 'amber',
    size: 'normal',
  },
  {
    icon: Database,
    title: 'Neuro Memory',
    desc: 'Long-term memory with L1/L2/L3 tiered cache and embedding search — context that grows with you.',
    accent: 'teal',
    size: 'normal',
  },
  {
    icon: Globe,
    title: 'Iterative RAG',
    desc: 'Browses the web intelligently, refining search queries until it finds exactly what is needed.',
    accent: 'amber',
    size: 'wide',
  },
  {
    icon: Code,
    title: 'Dev-Ready',
    desc: 'Built for engineers. Upload code, analyze diagrams, generate tests.',
    accent: 'teal',
    size: 'normal',
  },
  {
    icon: Scale,
    title: 'Perspective Debate',
    desc: 'A jury of specialized AI agents debates approaches, then a judge synthesizes the verdict.',
    accent: 'amber',
    size: 'normal',
  },
];

const HOW_IT_WORKS = [
  {
    step: '01',
    icon: Brain,
    title: 'HyperGate Classification',
    desc: 'Six sub-agents classify your problem in parallel — language, complexity, best method — before any reasoning begins.',
  },
  {
    step: '02',
    icon: Layers,
    title: 'Multi-Phase Pipeline',
    desc: 'Your chosen method runs through up to 6 structured phases: Decompose → Generate → Critique → Stress-test → Synthesize.',
  },
  {
    step: '03',
    icon: GitMerge,
    title: 'Epistemic Labels',
    desc: 'Every claim in the final answer is labeled VERIFIED, HYPOTHESIS, or UNKNOWN so you know exactly what to trust.',
  },
];

/* ─── Sub-components ────────────────────────────────────── */

function MethodTicker() {
  const doubled = [...METHODS, ...METHODS];
  return (
    <div className="relative overflow-hidden py-5" aria-label="Supported reasoning methods">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-[var(--bg)] to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-[var(--bg)] to-transparent" />
      <div className="flex w-max animate-ticker gap-3">
        {doubled.map((method, i) => (
          <span
            key={i}
            className="shrink-0 cursor-default rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-1.5 text-sm font-medium text-[var(--text-muted)] transition-all duration-200 hover:border-[var(--border-strong)] hover:text-[var(--text)] hover:bg-[var(--surface-2)] hover:scale-105"
          >
            {method}
          </span>
        ))}
      </div>
    </div>
  );
}

function FeatureCard({ feature, delay }: { feature: typeof FEATURES[number]; delay: number }) {
  const Icon = feature.icon;
  const isWide = feature.size === 'wide';
  const isTall = feature.size === 'tall';
  const isTeal = feature.accent === 'teal';

  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 card-hover hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)] hover:shadow-[var(--shadow-lg)] ${
        isWide ? 'sm:col-span-2' : ''
      } ${isTall ? 'row-span-2' : ''}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Hover glow */}
      <div
        className={`pointer-events-none absolute -top-20 -right-20 h-44 w-44 rounded-full opacity-0 blur-[60px] transition-opacity duration-500 group-hover:opacity-100 ${
          isTeal ? 'bg-teal-500' : 'bg-amber-400'
        }`}
      />

      <div className="relative">
        <div
          className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl transition-transform duration-200 group-hover:scale-110 ${
            isTeal
              ? 'bg-teal-500/10 text-teal-400'
              : 'bg-amber-400/10 text-amber-400'
          }`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <h3 className="mb-2 text-base font-semibold tracking-tight text-[var(--text)]">
          {feature.title}
        </h3>
        <p className="text-sm leading-relaxed text-[var(--text-muted)]">{feature.desc}</p>
      </div>
    </div>
  );
}

/* ─── Main Page ─────────────────────────────────────────── */

export default function LandingPage() {
  const user = useAppStore((s) => s.user);
  const router = useRouter();

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[var(--bg)] text-[var(--text)]">
      {/* WebGL Nebula Background */}
      <NebulaBackground />

      {/* Subtle ambient orbs on top of canvas */}
      <div className="pointer-events-none fixed inset-0 z-[1] overflow-hidden" aria-hidden="true">
        <div className="dot-grid absolute inset-0 opacity-40" />
        {/* Teal orb — top left */}
        <div className="absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-teal-500 opacity-[0.07] blur-[130px] animate-pulse-slow" />
        {/* Amber orb — bottom right */}
        <div className="absolute -bottom-60 -right-60 h-[500px] w-[500px] rounded-full bg-amber-400 opacity-[0.06] blur-[110px] animate-pulse-slow-2" />
      </div>

      <SiteHeader />

      <main id="main-content" className="relative z-10">

        {/* ── Hero ────────────────────────────────────────── */}
        <section className="flex min-h-screen flex-col items-center justify-center px-6 pb-24 pt-32 text-center">
          {/* Badge */}
          <div className="mb-8 inline-flex animate-fade-up items-center gap-2 rounded-full border border-teal-500/30 bg-teal-500/8 px-4 py-1.5 text-sm font-medium text-teal-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping-teal rounded-full bg-teal-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-teal-400" />
            </span>
            17 reasoning methods · 90+ AI models
          </div>

          {/* Headline */}
          <h1
            className="animate-fade-up text-[clamp(3.5rem,9vw,7.5rem)] font-bold leading-[1.0] tracking-[-0.04em] text-[var(--text)]"
            style={{ animationDelay: '80ms' }}
          >
            Reason Through
            <br />
            <span className="gradient-text animate-gradient-text">Anything.</span>
          </h1>

          {/* Subtext */}
          <p
            className="animate-fade-up mt-8 max-w-xl text-[1.125rem] leading-relaxed text-[var(--text-muted)]"
            style={{ animationDelay: '160ms' }}
          >
            ARA decomposes complex problems into structured pipelines, runs cross-lab AI debates,
            stress-tests every solution, and synthesizes verified answers.
          </p>

          {/* CTA */}
          <div
            className="animate-fade-up mt-10 flex flex-col items-center gap-4 sm:flex-row"
            style={{ animationDelay: '240ms' }}
          >
            <button
              onClick={() => router.push('/chat')}
              className="group flex items-center gap-2.5 rounded-xl bg-[var(--accent)] px-7 py-3.5 text-base font-semibold text-[var(--accent-text)] transition-all btn-lift btn-glow hover:bg-[var(--accent-hover)]"
            >
              Start Reasoning
              <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
            </button>
            <button
              onClick={() => router.push('/about')}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-7 py-3.5 text-base font-semibold text-[var(--text-2)] transition-all btn-lift hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            >
              Learn more
            </button>
          </div>

          {/* Trust line */}
          <p
            className="animate-fade-up mt-5 text-sm text-[var(--text-subtle)]"
            style={{ animationDelay: '300ms' }}
          >
            No signup required · Free to try
          </p>

          {/* Stats */}
          <div
            className="animate-fade-up mt-20 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--border)] sm:grid-cols-4"
            style={{ animationDelay: '380ms' }}
          >
            {STATS.map(({ value, label }) => (
              <div
                key={label}
                className="group flex flex-col items-center gap-1 bg-[var(--surface)] px-8 py-6 transition-colors duration-200 hover:bg-[var(--surface-2)]"
              >
                <span className="text-3xl font-bold tracking-tight gradient-text transition-transform duration-200 group-hover:scale-110">{value}</span>
                <span className="text-xs font-medium text-[var(--text-muted)]">{label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── Methods ticker ──────────────────────────────── */}
        <section className="border-y border-[var(--border)] bg-[var(--surface)]/50">
          <div className="mb-2 mt-5 text-center text-xs font-semibold uppercase tracking-widest text-[var(--text-subtle)]">
            Reasoning Methods
          </div>
          <MethodTicker />
        </section>

        {/* ── Features ────────────────────────────────────── */}
        <section className="px-6 py-32">
          <div className="mx-auto max-w-6xl">
            <div className="mb-4 text-center text-sm font-semibold uppercase tracking-widest text-[var(--accent)]">
              Why ARA
            </div>
            <h2 className="mb-4 text-center text-[clamp(2rem,4vw,3rem)] font-bold tracking-tight text-[var(--text)]">
              Intelligence, Engineered.
            </h2>
            <p className="mx-auto mb-16 max-w-lg text-center text-[var(--text-muted)]">
              ARA isn&apos;t a wrapper around one model. It&apos;s a reasoning system designed from first principles.
            </p>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature, i) => (
                <FeatureCard key={feature.title} feature={feature} delay={i * 60} />
              ))}
            </div>
          </div>
        </section>

        {/* ── How it works ────────────────────────────────── */}
        <section className="border-t border-[var(--border)] bg-[var(--surface)]/30 px-6 py-32">
          <div className="mx-auto max-w-6xl">
            <div className="mb-4 text-center text-sm font-semibold uppercase tracking-widest text-[var(--accent)]">
              Architecture
            </div>
            <h2 className="mb-16 text-center text-[clamp(2rem,4vw,3rem)] font-bold tracking-tight text-[var(--text)]">
              How it works
            </h2>

            <div className="grid gap-8 md:grid-cols-3">
              {HOW_IT_WORKS.map(({ step, icon: Icon, title, desc }) => (
                <div key={step} className="group relative card-hover rounded-2xl p-2">
                  <div className="mb-8 flex items-center gap-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] transition-all duration-200 group-hover:border-teal-500/40 group-hover:bg-teal-500/8 group-hover:scale-110">
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="font-mono text-4xl font-bold text-[var(--text-subtle)] transition-colors duration-200 group-hover:text-[var(--accent)]">
                      {step}
                    </span>
                  </div>
                  <h3 className="mb-3 text-lg font-semibold tracking-tight text-[var(--text)]">
                    {title}
                  </h3>
                  <p className="text-sm leading-relaxed text-[var(--text-muted)]">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Epistemic labels showcase ────────────────────── */}
        <section className="border-t border-[var(--border)] px-6 py-32">
          <div className="mx-auto max-w-4xl text-center">
            <div className="mb-4 text-sm font-semibold uppercase tracking-widest text-[var(--accent)]">
              Epistemic Labeling
            </div>
            <h2 className="mb-6 text-[clamp(2rem,4vw,3rem)] font-bold tracking-tight text-[var(--text)]">
              Know what to trust.
            </h2>
            <p className="mb-12 text-[var(--text-muted)]">
              Every claim in ARA&apos;s output carries an epistemic label so you can distinguish facts from inferences.
            </p>

            <div className="inline-grid gap-4 sm:grid-cols-3">
              {[
                { label: 'VERIFIED', color: 'text-emerald-400 border-emerald-500/25 bg-emerald-500/8', desc: 'Corroborated by multiple independent sources or models.' },
                { label: 'HYPOTHESIS', color: 'text-amber-400 border-amber-500/25 bg-amber-500/8', desc: 'Plausible inference supported by reasoning but not confirmed.' },
                { label: 'UNKNOWN', color: 'text-slate-400 border-slate-500/25 bg-slate-500/8', desc: 'Insufficient evidence — treat with caution.' },
              ].map(({ label, color, desc }) => (
                <div
                  key={label}
                  className={`card-hover rounded-2xl border px-6 py-5 ${color}`}
                >
                  <div className="mb-2 text-sm font-bold tracking-wider">{label}</div>
                  <p className="text-xs leading-relaxed opacity-80">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA ─────────────────────────────────────────── */}
        <section className="border-t border-[var(--border)] px-6 py-32">
          <div className="mx-auto max-w-3xl text-center">
            {/* Glow orb behind CTA */}
            <div className="pointer-events-none absolute left-1/2 -translate-x-1/2 h-[400px] w-[600px] rounded-full bg-teal-600 opacity-[0.07] blur-[100px]" aria-hidden="true" />

            <div className="relative">
              <h2 className="mb-6 text-[clamp(2.5rem,5vw,4rem)] font-bold tracking-[-0.03em] text-[var(--text)]">
                Think deeper,
                <br />
                <span className="gradient-text animate-gradient-text">starting now.</span>
              </h2>
              <p className="mb-10 text-lg text-[var(--text-muted)]">
                No setup. No API key. Just start reasoning.
              </p>
              <button
                onClick={() => router.push('/chat')}
                className="group inline-flex items-center gap-2.5 rounded-xl bg-[var(--accent)] px-8 py-4 text-lg font-semibold text-[var(--accent-text)] transition-all btn-lift btn-glow hover:bg-[var(--accent-hover)]"
              >
                Open Reasoner
                <ArrowRight className="h-5 w-5 transition-transform duration-200 group-hover:translate-x-1" />
              </button>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
