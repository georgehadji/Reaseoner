import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

// Placeholder for HashiCorp Sans local font import
// You would typically import your font files like this:
// import localFont from 'next/font/local';
// const hashicorpSans = localFont({
//   src: [
//     {
//       path: '../../public/fonts/HashiCorpSans-Regular.woff2', // Adjust path
//       weight: '400',
//       style: 'normal',
//     },
//     {
//       path: '../../public/fonts/HashiCorpSans-SemiBold.woff2', // Adjust path
//       weight: '600',
//       style: 'normal',
//     },
//     {
//       path: '../../public/fonts/HashiCorpSans-Bold.woff2', // Adjust path
//       weight: '700',
//       style: 'normal',
//     },
//   ],
//   variable: '--font-hashicorpSans',
//   display: 'swap',
// });

// For now, we'll simulate the font loading with a simple CSS variable to work with Tailwind
// In a real project, replace with actual font loading as above.
const hashicorpSans = { variable: 'font-hashicorpSans' }; // Placeholder

// System UI fallback for body text, typically handled by global CSS and Tailwind config
const systemUi = { variable: 'font-systemUi' }; // Placeholder

export const metadata: Metadata = {
  title: 'Reasoner — Adaptive Reasoning Architecture',
  description: 'Multi-method reasoning pipeline with live streaming, method-specific phases, and evidence-grounded synthesis.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${hashicorpSans.variable} ${systemUi.variable} antialiased`} suppressHydrationWarning>
      <body className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex flex-col font-systemUi"> {/* Default to system-ui for body */}
        <a href="#main-content" className="skip-link">Skip to main content</a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
