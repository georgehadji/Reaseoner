'use client';

import { useState } from 'react';
import { Lock, ShieldCheck, Database, Server, Users, History, Globe, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SecurityModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  return (
    <div
      className={cn(
        'fixed inset-0 z-[300] flex items-center justify-center p-4 transition-all duration-300',
        isOpen ? 'bg-black/60 opacity-100' : 'bg-black/0 opacity-0 pointer-events-none',
      )}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={cn(
          'w-full max-w-2xl rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-[var(--shadow-xl)] transition-all duration-300',
          isOpen ? 'translate-y-0 opacity-100 scale-100' : 'translate-y-4 opacity-0 scale-95',
        )}
      >
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-500/10 text-green-500">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[var(--text)]">Enterprise Security & Trust</h3>
              <p className="text-sm text-[var(--text-2)]">Advanced safeguards for mission-critical reasoning.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Column 1 */}
          <div className="space-y-6">
            <section className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-2)] text-[var(--text-2)]">
                <Lock className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-semibold text-[var(--text-2)] mb-1 uppercase tracking-wider text-[10px]">Compliance</h4>
                <h5 className="font-bold text-[var(--text)] text-sm mb-1">Certified SOC 2 Type II Ready</h5>
                <p className="text-[12px] text-[var(--text-2)] leading-relaxed">
                  Independently audited privacy and security standards. Designed for full compliance to protect enterprise-grade workloads.
                </p>
              </div>
            </section>

            <section className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-2)] text-[var(--text-2)]">
                <Database className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-semibold text-[var(--text-2)] mb-1 uppercase tracking-wider text-[10px]">Data Privacy</h4>
                <h5 className="font-bold text-[var(--text)] text-sm mb-1">Data Privacy</h5>
                <p className="text-[12px] text-[var(--text-2)] leading-relaxed">
                  Zero-Training Guarantee. We never train LLMs on your data. Full GDPR and HIPAA compliance.
                  <br />
                  <span className="italic text-[var(--text-muted)] text-[11px]">We never train our LLMs on enterprise data.</span>
                </p>
              </div>
            </section>

            <section className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-2)] text-[var(--text-2)]">
                <Server className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-semibold text-[var(--text-2)] mb-1 uppercase tracking-wider text-[10px]">Encryption</h4>
                <h5 className="font-bold text-[var(--text)] text-sm mb-1">Encryption</h5>
                <p className="text-[12px] text-[var(--text-2)] leading-relaxed">
                  E2EE in transit and at rest using AES-256-GCM. 
                  <br />
                  <span className="italic text-[var(--text-muted)] text-[11px]">All data is encrypted in transit and at rest.</span>
                </p>
              </div>
            </section>
          </div>

          {/* Column 2 */}
          <div className="space-y-6">
            <section className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-2)] text-[var(--text-2)]">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-semibold text-[var(--text-2)] mb-1 uppercase tracking-wider text-[10px]">Access Control</h4>
                <h5 className="font-bold text-[var(--text)] text-sm mb-1">SSO & SAML Support</h5>
                <p className="text-[12px] text-[var(--text-2)] leading-relaxed">
                  Integrate with Okta, Azure AD, and Google Workspace. Enforce RBAC (Role-Based Access Control) for your team.
                </p>
              </div>
            </section>

            <section className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-2)] text-[var(--text-2)]">
                <History className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-semibold text-[var(--text-2)] mb-1 uppercase tracking-wider text-[10px]">Governance</h4>
                <h5 className="font-bold text-[var(--text)] text-sm mb-1">Audit Logs & Retention</h5>
                <p className="text-[12px] text-[var(--text-2)] leading-relaxed">
                  Comprehensive audit trails for all actions. Configurable data retention policies to meet legal requirements.
                </p>
              </div>
            </section>

            <section className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-2)] text-[var(--text-2)]">
                <Globe className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-semibold text-[var(--text-2)] mb-1 uppercase tracking-wider text-[10px]">Network</h4>
                <h5 className="font-bold text-[var(--text)] text-sm mb-1">Zero-Trust Architecture</h5>
                <p className="text-[12px] text-[var(--text-2)] leading-relaxed">
                  All inter-component communication is authenticated and encrypted via internal PKI. No plaintext data on the wire.
                </p>
              </div>
            </section>
          </div>
        </div>

        <button
          onClick={onClose}
          className="mt-8 w-full rounded-xl bg-[var(--accent)] py-3 text-sm font-semibold text-[var(--accent-text)] transition-all hover:opacity-90 active:scale-[0.98]"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
