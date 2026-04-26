import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Reasoner — Think Deeper',
  description:
    'Multi-method AI reasoning that decomposes complex problems, debates solutions, and delivers verified answers.',
  openGraph: {
    title: 'Reasoner — Think Deeper',
    description: '17 reasoning methods · 90+ AI models · Verified answers',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} antialiased`} suppressHydrationWarning>
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex flex-col">
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
