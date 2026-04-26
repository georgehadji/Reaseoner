'use client';

import Link from 'next/link';
import { Brain } from 'lucide-react';

export function LandingFooter() {
  return (
    <footer className="bg-mds-color-dark-charcoal text-mds-color-mid-gray">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center gap-2 font-hashicorpSans text-small-title font-bold text-mds-color-near-white mb-6 md:mb-0">
            <Brain className="h-6 w-6 text-mds-color-vagrant-brand" />
            <span>Reasoner</span>
          </div>
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 font-systemUi text-caption font-normal">
            <Link href="/about" className="text-mds-color-mid-gray hover:text-mds-color-action-blue transition-colors">About</Link>
            <Link href="/pricing" className="text-mds-color-mid-gray hover:text-mds-color-action-blue transition-colors">Pricing</Link>
            <Link href="/faq" className="text-mds-color-mid-gray hover:text-mds-color-action-blue transition-colors">FAQ</Link>
            <Link href="/contact" className="text-mds-color-mid-gray hover:text-mds-color-action-blue transition-colors">Contact</Link>
            <Link href="/terms" className="text-mds-color-mid-gray hover:text-mds-color-action-blue transition-colors">Terms</Link>
            <Link href="/privacy" className="text-mds-color-mid-gray hover:text-mds-color-action-blue transition-colors">Privacy</Link>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-mds-color-cool-gray/[0.4] text-center font-systemUi text-caption font-normal text-mds-color-dark-gray">
          <p>&copy; {new Date().getFullYear()} Advanced Reasoning Architecture. A new kind of intelligence.</p>
        </div>
      </div>
    </footer>
  );
}
