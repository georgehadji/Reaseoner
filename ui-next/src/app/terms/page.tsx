import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function TermsPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 flex-1 w-full">
      <h1 className="text-4xl font-bold mb-8">Terms of Service</h1>
      <div className="prose prose-invert max-w-none text-[var(--text-2)]">
        <p className="mb-4">Last updated: {new Date().toLocaleDateString()}</p>
        
        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">1. Acceptance of Terms</h2>
        <p className="mb-4">By accessing and using the Advanced Reasoning Architecture (ARA) platform, you accept and agree to be bound by the terms and provision of this agreement.</p>
        
        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">2. Description of Service</h2>
        <p className="mb-4">ARA provides a multi-method AI reasoning system. The platform utilizes various LLM providers. You understand that AI-generated content may be inaccurate, and you are responsible for verifying any output before relying on it.</p>
        
        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">3. User Responsibilities</h2>
        <p className="mb-4">You agree not to use the platform for any unlawful purpose or in any way that interrupts, damages, or impairs the service. You are responsible for maintaining the confidentiality of your account.</p>

        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">4. Intellectual Property</h2>
        <p className="mb-4">You retain all rights to the data you input into the service. However, by using the service, you grant Reasoner a license to process this data to provide the reasoning outputs.</p>

        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">5. Limitation of Liability</h2>
        <p className="mb-4">ARA shall not be liable for any indirect, incidental, special, consequential or punitive damages resulting from your use of or inability to use the service.</p>
      </div>
      </main>
      <SiteFooter />
    </div>
  );
}
