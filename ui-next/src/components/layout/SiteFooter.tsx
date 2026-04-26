import Link from 'next/link';

const LINKS = {
  Product: [
    { label: 'About', href: '/about' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'FAQ', href: '/faq' },
    { label: 'Docs', href: '/help' },
  ],
  Legal: [
    { label: 'Terms of Service', href: '/terms' },
    { label: 'Privacy Policy', href: '/privacy' },
    { label: 'Cookie Policy', href: '/cookies' },
    { label: 'Contact', href: '/contact' },
  ],
};

export function SiteFooter() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--bg)] mt-auto">
      <div className="mx-auto max-w-7xl px-6 py-16">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2.5 font-semibold text-[var(--text)]">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)] text-white">
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9.5 2a2.5 2.5 0 1 1 5 0" />
                  <path d="M4 9.5a2.5 2.5 0 0 1 5-1m6 0a2.5 2.5 0 0 1 5 1" />
                  <path d="M2 14a2.5 2.5 0 0 0 5 0v-4.5M17 14a2.5 2.5 0 0 0 5 0v-4.5" />
                  <path d="M7 8v10a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V8" />
                  <path d="M12 2v20" />
                </svg>
              </div>
              <span className="text-[15px] tracking-tight">Reasoner</span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-[var(--text-muted)]">
              Advanced Reasoning Architecture — 17 methods, 90+ models, verified answers.
            </p>
          </div>

          {/* Links */}
          {Object.entries(LINKS).map(([group, items]) => (
            <div key={group}>
              <div className="mb-4 text-xs font-semibold uppercase tracking-widest text-[var(--text-subtle)]">
                {group}
              </div>
              <ul className="flex flex-col gap-2.5">
                {items.map(({ label, href }) => (
                  <li key={href}>
                    <Link
                      href={href}
                      className="text-sm text-[var(--text-muted)] transition-colors hover:text-[var(--text)]"
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-[var(--border)] pt-8 text-xs text-[var(--text-subtle)] sm:flex-row">
          <p>© {new Date().getFullYear()} Advanced Reasoning Architecture. All rights reserved.</p>
          <p className="flex items-center gap-1.5">
            Built with
            <span className="gradient-text font-semibold">17 reasoning methods</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
