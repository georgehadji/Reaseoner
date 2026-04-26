import Link from 'next/link';

export function SiteFooter() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--bg)] py-12 text-center text-sm text-[var(--text-muted)] mt-auto">
      <div className="flex flex-wrap justify-center gap-6 mb-4">
        <Link href="/terms" className="hover:text-[var(--text)] transition-colors">Terms of Service</Link>
        <Link href="/privacy" className="hover:text-[var(--text)] transition-colors">Privacy Policy</Link>
        <Link href="/cookies" className="hover:text-[var(--text)] transition-colors">Cookie Policy</Link>
        <Link href="/contact" className="hover:text-[var(--text)] transition-colors">Contact</Link>
      </div>
      <p>© {new Date().getFullYear()} Advanced Reasoning Architecture. All rights reserved.</p>
    </footer>
  );
}
