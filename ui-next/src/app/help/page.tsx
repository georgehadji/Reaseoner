import Link from 'next/link';
import { BookOpen, Key, Zap, Shield } from 'lucide-react';

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16">
      <Link href="/" className="text-[var(--accent)] hover:underline mb-8 inline-block">&larr; Back to Home</Link>
      <h1 className="text-4xl font-bold mb-4">Help Center & Documentation</h1>
      <p className="text-[var(--text-muted)] mb-12 text-lg">Learn how to get the most out of the Advanced Reasoning Architecture.</p>
      
      <div className="grid md:grid-cols-2 gap-6">
        <a href="#" className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--accent)] transition-colors group">
          <BookOpen className="h-8 w-8 text-[var(--accent)] mb-4" />
          <h2 className="text-xl font-bold mb-2 group-hover:text-[var(--accent)] transition-colors">Getting Started</h2>
          <p className="text-[var(--text-2)] text-sm">Learn the basics of using the composer, uploading files, and starting your first reasoning pipeline.</p>
        </a>

        <a href="#" className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--accent)] transition-colors group">
          <Zap className="h-8 w-8 text-[var(--accent)] mb-4" />
          <h2 className="text-xl font-bold mb-2 group-hover:text-[var(--accent)] transition-colors">Understanding Presets</h2>
          <p className="text-[var(--text-2)] text-sm">Discover the difference between Budget, Balanced, and Premium tiers, and how they affect model routing.</p>
        </a>

        <a href="#" className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--accent)] transition-colors group">
          <Shield className="h-8 w-8 text-[var(--accent)] mb-4" />
          <h2 className="text-xl font-bold mb-2 group-hover:text-[var(--accent)] transition-colors">Privacy & Neuro Memory</h2>
          <p className="text-[var(--text-2)] text-sm">How to manage your history, clear your cache, and control what Neuro Memory learns about you.</p>
        </a>

        <a href="#" className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--accent)] transition-colors group">
          <Key className="h-8 w-8 text-[var(--accent)] mb-4" />
          <h2 className="text-xl font-bold mb-2 group-hover:text-[var(--accent)] transition-colors">Billing & Limits</h2>
          <p className="text-[var(--text-2)] text-sm">Understanding your monthly quota, tokens, and how to upgrade or cancel your subscription.</p>
        </a>
      </div>
    </div>
  );
}
