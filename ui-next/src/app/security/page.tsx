import { ShieldCheck, Lock, Database, Server, Users, History, Globe, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function SecurityPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)]">
      <SiteHeader />
      
      <main className="mx-auto max-w-4xl px-6 py-24 flex-1 w-full">
        <div className="text-center mb-16">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-green-500/10 text-green-500 mb-6">
            <ShieldCheck className="h-10 w-10" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-[var(--text)] mb-6">Security & Trust at Reasoner</h1>
          <p className="text-xl text-[var(--text-muted)] max-w-2xl mx-auto">
            We prioritize the privacy and security of your critical thinking. Our architecture is built to the highest enterprise standards.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2 lg:gap-12">
          {/* Data Privacy */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8">
            <Database className="h-8 w-8 text-[var(--accent)] mb-6" />
            <h2 className="text-2xl font-bold text-[var(--text)] mb-4">Data Privacy</h2>
            <ul className="space-y-4">
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>No Training:</strong> Your enterprise data is never used to train or fine-tune models.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>Ownership:</strong> You retain 100% ownership of your inputs, queries, and generated insights.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>GDPR & HIPAA:</strong> Full compliance with global privacy regulations and healthcare standards.</span>
              </li>
            </ul>
          </div>

          {/* Encryption */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8">
            <Lock className="h-8 w-8 text-[var(--accent)] mb-6" />
            <h2 className="text-2xl font-bold text-[var(--text)] mb-4">Advanced Encryption</h2>
            <ul className="space-y-4">
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>At Rest:</strong> All stored data is encrypted using industry-standard AES-256-GCM.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>In Transit:</strong> Data transmission is protected via TLS 1.3 with Perfect Forward Secrecy.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>Key Management:</strong> Secure key rotation and isolation protocols.</span>
              </li>
            </ul>
          </div>

          {/* Infrastructure */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8">
            <Server className="h-8 w-8 text-[var(--accent)] mb-6" />
            <h2 className="text-2xl font-bold text-[var(--text)] mb-4">Secure Infrastructure</h2>
            <ul className="space-y-4">
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>Zero-Trust:</strong> Every internal request is authenticated and authorized within our containerized network.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>SOC 2 Type II:</strong> Our processes and infrastructure are designed for SOC 2 Type II compliance.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>Network Isolation:</strong> Virtual private cloud (VPC) with strict egress/ingress controls.</span>
              </li>
            </ul>
          </div>

          {/* Identity & Access */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8">
            <Users className="h-8 w-8 text-[var(--accent)] mb-6" />
            <h2 className="text-2xl font-bold text-[var(--text)] mb-4">Identity & Access</h2>
            <ul className="space-y-4">
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>Single Sign-On:</strong> Support for SAML 2.0 and OIDC (Okta, Azure AD, Google).</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>RBAC:</strong> Granular role-based access control for teams and organizations.</span>
              </li>
              <li className="flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                <span className="text-[var(--text-muted)] text-sm"><strong>Audit Logs:</strong> Real-time activity logs for administrative governance.</span>
              </li>
            </ul>
          </div>
        </div>

        <section className="mt-20 rounded-3xl bg-green-500/5 border border-green-500/20 p-12 text-center">
          <ShieldAlert className="h-12 w-12 text-green-500 mx-auto mb-6" />
          <h2 className="text-3xl font-bold text-[var(--text)] mb-4">Ready for Enterprise?</h2>
          <p className="text-[var(--text-muted)] mb-8 max-w-xl mx-auto">
            Contact our security team to request our latest SOC 2 report or to discuss custom data retention and compliance requirements.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <button className="rounded-xl bg-[var(--accent)] px-8 py-4 font-bold text-[var(--accent-text)] transition-all hover:opacity-90 active:scale-[0.98]">
              Contact Security
            </button>
            <button className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-8 py-4 font-bold text-[var(--text)] transition-all hover:bg-[var(--surface-2)] active:scale-[0.98]">
              View Docs
            </button>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
