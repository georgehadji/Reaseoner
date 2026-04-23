import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'ARA — Adaptive Reasoning Architecture',
  description: 'Multi-method reasoning pipeline with live streaming, method-specific phases, and evidence-grounded synthesis.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="h-full overflow-hidden bg-[var(--bg)] text-[var(--text)]">
        <a href="#main-content" className="skip-link">Skip to main content</a>
        <main id="main-content" className="h-full">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
