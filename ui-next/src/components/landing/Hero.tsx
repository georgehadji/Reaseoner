'use client';

import { useRouter } from 'next/navigation';
import { useAppStore } from '@/stores/app-store';
import { motion, type Variants } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export function Hero() {
  const router = useRouter();
  const user = useAppStore((s) => s.user);

  const FADE_UP_ANIMATION_VARIANTS: Variants = {
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 50, damping: 20 } },
  };

  return (
    <motion.section
      initial="hidden"
      animate="show"
      viewport={{ once: true }}
      variants={{
        hidden: {},
        show: {
          transition: {
            staggerChildren: 0.15,
          },
        },
      }}
      className="relative bg-mds-color-dark-charcoal text-center px-4 py-20 lg:py-32"
    >
      <motion.h1
        variants={FADE_UP_ANIMATION_VARIANTS}
        className="font-hashicorpSans text-display-hero font-bold leading-[1.17] text-mds-color-near-white font-hashicorp-kern"
      >
        Reasoning Evolved.
      </motion.h1>
      <motion.p
        variants={FADE_UP_ANIMATION_VARIANTS}
        className="mx-auto mt-6 max-w-2xl font-systemUi text-body-lg font-normal leading-[1.50] text-mds-color-mid-gray"
      >
        Reasoner is a new kind of intelligence. It decomposes complex problems, runs parallel research agents, and synthesizes insights to give you answers, not just links.
      </motion.p>
      <motion.div
        variants={FADE_UP_ANIMATION_VARIANTS}
        className="mt-10 flex justify-center gap-4"
      >
        <button
          onClick={() => router.push(user ? '/chat' : '/chat')}
          className="flex items-center gap-2 pl-[15px] pr-[9px] py-[9px] text-sm font-bold rounded-[5px] bg-mds-color-dark-charcoal text-mds-color-mid-gray shadow-micro-shadow border border-mds-color-cool-gray/[0.4] transition-transform hover:scale-105 focus:outline-none focus:ring-3 focus:ring-[var(--mds-color-focus-action-external)]"
        >
          Start Reasoning <ArrowRight className="h-4 w-4" />
        </button>
        <a
          href="#features"
          className="flex items-center gap-2 px-8 py-3.5 text-sm font-bold rounded-[4px] bg-white text-mds-color-charcoal hover:bg-mds-color-light-gray transition-transform hover:scale-105 focus:outline-none focus:ring-3 focus:ring-transparent"
        >
          Learn More
        </a>
      </motion.div>
    </motion.section>
  );
}
