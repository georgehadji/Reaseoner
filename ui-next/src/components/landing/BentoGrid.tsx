'use client';

import { motion, type Variants } from 'framer-motion';
import { Brain, Zap, Shield, Database, Code, Globe, ArrowRight } from 'lucide-react';

const FADE_UP_ANIMATION_VARIANTS: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 50, damping: 20 } },
};

const features = [
  {
    title: "Multi-Model Routing",
    description: "Automatically selects the best LLM for each sub-task.",
    icon: <Zap className="w-6 h-6" />,
    className: "col-span-2",
  },
  {
    title: "Fact Verification",
    description: "Rigorous critique and fact-checking before final synthesis.",
    icon: <Shield className="w-6 h-6" />,
    className: "col-span-1",
  },
  {
    title: "Neuro Memory",
    description: "Learns from interactions to provide personalized context.",
    icon: <Database className="w-6 h-6" />,
    className: "col-span-1",
  },
  {
    title: "Developer Ready",
    description: "Analyze architectures, generate unit tests, and write code.",
    icon: <Code className="w-6 h-6" />,
    className: "col-span-2",
  },
  {
    title: "Iterative RAG",
    description: "Intelligently browses the web until it finds the perfect information.",
    icon: <Globe className="w-6 h-6" />,
    className: "col-span-3",
  },
];

export function BentoGrid() {
    return (
      <motion.section 
        id="features"
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.2 }}
        variants={{
          hidden: {},
          show: {
            transition: {
              staggerChildren: 0.1,
            },
          },
        }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-6xl mx-auto p-4 lg:p-12"
      >
        {features.map((feature, i) => (
          <motion.div
            key={i}
            variants={FADE_UP_ANIMATION_VARIANTS}
            whileHover={{ borderColor: 'var(--mds-color-waypoint-button-background-focus)', y: -4 }} // Subtle lift and accent border on hover
            className={`relative group rounded-[8px] bg-white p-6 shadow-micro-shadow border border-mds-color-mid-gray transition-all ${feature.className}`}
          >
            <div className="absolute top-4 right-4 text-mds-color-vagrant-brand group-hover:text-mds-color-waypoint-button-background-focus transition-colors">
              {feature.icon}
            </div>
            <h3 className="font-hashicorpSans text-card-title font-bold leading-[1.19] text-mds-color-hcp-brand">{feature.title}</h3>
            <p className="font-systemUi text-body font-normal leading-[1.63] text-mds-color-charcoal mt-1">{feature.description}</p>
          </motion.div>
        ))}
      </motion.section>
  );
}
