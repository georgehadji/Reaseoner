import { ReactNode } from 'react';

interface TooltipProps {
  text: string;
  children: ReactNode;
  as?: 'span' | 'div';
}

export function Tooltip({ text, children, as: Component = 'span' }: TooltipProps) {
  return (
    <Component className="group relative inline-block">
      {children}
      <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 w-max max-w-[220px] -translate-x-1/2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-[11px] leading-4 font-medium text-[var(--text-2)] opacity-0 shadow-[var(--shadow)] transition-opacity group-hover:opacity-100 z-50">
        {text}
        <div className="absolute left-1/2 top-full -mt-0.5 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-[var(--border)] bg-[var(--surface)]" />
      </div>
    </Component>
  );
}
