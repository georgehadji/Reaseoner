'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp } from 'lucide-react';

const faqs = [
  {
    q: "What is Reasoner?",
    a: "Reasoner is an AI platform that breaks down complex queries into manageable phases, verifying facts, running multiple models, and searching the web to synthesize a high-quality final answer."
  },
  {
    q: "How does billing work?",
    a: "We use Stripe for secure billing. Free users get a set amount of queries per month. Pro and Enterprise users unlock higher limits, premium models, and priority support. You can manage your subscription from the Dashboard."
  },
  {
    q: "What is Neuro Memory?",
    a: "Neuro Memory is our personalized contextual engine. It remembers details from your previous conversations and intelligently surfaces them when relevant, allowing the AI to maintain long-term context without exceeding token limits."
  },
  {
    q: "Can I cancel my subscription?",
    a: "Yes, you can cancel your subscription at any time through the Billing Portal in your Dashboard. Your premium access will remain active until the end of your current billing period."
  },
  {
    q: "Which AI models do you use?",
    a: "We use a dynamic routing system that selects from top-tier models like Anthropic Claude 3.5, OpenAI GPT-4o, Google Gemini, and DeepSeek, depending on the phase of reasoning and your subscription tier."
  }
];

import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 flex-1 w-full">
      <h1 className="text-4xl font-bold mb-2">Frequently Asked Questions</h1>
      <p className="text-[var(--text-muted)] mb-12">Find answers to common questions about Reasoner.</p>
      
      <div className="space-y-4">
        {faqs.map((faq, idx) => (
          <div key={idx} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden transition-colors">
            <button
              onClick={() => setOpenIndex(openIndex === idx ? null : idx)}
              className="flex w-full items-center justify-between p-5 text-left font-medium text-[var(--text)] hover:bg-[var(--surface-2)]"
            >
              {faq.q}
              {openIndex === idx ? <ChevronUp className="h-5 w-5 text-[var(--text-muted)]" /> : <ChevronDown className="h-5 w-5 text-[var(--text-muted)]" />}
            </button>
            {openIndex === idx && (
              <div className="p-5 pt-0 text-[var(--text-2)] border-t border-[var(--border)] mt-2">
                <p className="pt-3">{faq.a}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-12 text-center p-8 rounded-xl bg-[var(--surface-2)] border border-[var(--border)]">
        <h2 className="text-xl font-bold mb-2">Still have questions?</h2>
        <p className="text-[var(--text-muted)] mb-4">We&apos;re here to help.</p>
        <Link href="/contact" className="inline-block rounded-lg bg-[var(--accent)] px-6 py-2 text-sm font-medium text-[var(--accent-text)] hover:opacity-90">
          Contact Support
        </Link>
      </div>
      </main>
      <SiteFooter />
    </div>
  );
}
