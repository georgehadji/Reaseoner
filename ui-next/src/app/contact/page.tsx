'use client';

import { useState } from 'react';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Placeholder for actual form submission logic
    setSubmitted(true);
  };

  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-2xl px-4 py-16 flex-1 w-full">
      <h1 className="text-4xl font-bold mb-8">Contact Support</h1>
      
      {submitted ? (
        <div className="rounded-lg bg-[#808080]/10 p-6 text-center text-[#A0A0A0] border border-[#808080]/20">
          <h2 className="text-xl font-semibold mb-2">Message Sent</h2>
          <p>Thank you for reaching out. Our support team will get back to you within 24 hours.</p>
          <button onClick={() => setSubmitted(false)} className="mt-4 text-[var(--accent)] hover:underline">
            Send another message
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8">
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-medium text-[var(--text-2)]">Name</label>
            <input
              id="name"
              type="text"
              required
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-[var(--text)] focus:border-[var(--accent)] focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-[var(--text-2)]">Email</label>
            <input
              id="email"
              type="email"
              required
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-[var(--text)] focus:border-[var(--accent)] focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="subject" className="mb-1 block text-sm font-medium text-[var(--text-2)]">Topic</label>
            <select
              id="subject"
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-[var(--text)] focus:border-[var(--accent)] focus:outline-none"
            >
              <option>Billing Issue</option>
              <option>Technical Support</option>
              <option>Feature Request</option>
              <option>Other</option>
            </select>
          </div>
          <div>
            <label htmlFor="message" className="mb-1 block text-sm font-medium text-[var(--text-2)]">Message</label>
            <textarea
              id="message"
              required
              rows={5}
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-[var(--text)] focus:border-[var(--accent)] focus:outline-none resize-none"
            ></textarea>
          </div>
          <button
            type="submit"
            className="w-full rounded-lg bg-[var(--accent)] p-3 font-medium text-[var(--accent-text)] hover:opacity-90 transition-opacity"
          >
            Send Message
          </button>
        </form>
      )}
      </main>
      <SiteFooter />
    </div>
  );
}
