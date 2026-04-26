import { SiteHeader } from '@/components/layout/SiteHeader';
import { SiteFooter } from '@/components/layout/SiteFooter';

export default function PrivacyPage() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--bg)] text-[var(--text)]">
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-4 py-16 flex-1 w-full">
      <h1 className="text-4xl font-bold mb-8">Privacy Policy</h1>
      <div className="prose prose-invert max-w-none text-[var(--text-2)]">
        <p className="mb-4">Last updated: {new Date().toLocaleDateString()}</p>
        
        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">1. Information We Collect</h2>
        <p className="mb-4">We collect information you provide directly to us, including your email address when you register, and the prompts and context you input into the Reasoner system.</p>
        
        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">2. How We Use Your Information</h2>
        <p className="mb-4">We use the information to provide, maintain, and improve our services, including our Neuro Memory feature which personalizes your AI experience based on past interactions.</p>
        
        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">3. Data Sharing</h2>
        <p className="mb-4">In order to process your requests, your prompts may be sent to third-party LLM providers (such as OpenAI, Anthropic, or Google) via secure APIs. We do not sell your personal data to third parties.</p>

        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">4. Data Security</h2>
        <p className="mb-4">We implement appropriate technical and organizational measures to protect your personal data against unauthorized or unlawful processing.</p>

        <h2 className="text-2xl font-semibold mt-8 mb-4 text-[var(--text)]">5. Your Rights</h2>
        <p className="mb-4">You have the right to access, update, or delete your personal information at any time through your account settings or by contacting our support team.</p>
      </div>
      </main>
      <SiteFooter />
    </div>
  );
}
