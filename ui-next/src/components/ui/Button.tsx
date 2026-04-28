import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'premium' | 'danger';
  size?: 'sm' | 'md';
}

export function Button({
  children,
  variant = 'ghost',
  size = 'md',
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-lg font-medium disabled:cursor-not-allowed disabled:opacity-50 min-touch',
        /* Smooth multi-property transitions */
        'transition-all duration-200 ease-out',
        'active:scale-[0.97] active:duration-100',
        size === 'sm' && 'h-10 px-3 text-xs',
        size === 'md' && 'h-10 px-4 text-sm',
        variant === 'primary' &&
          'bg-[var(--accent)] text-[var(--accent-text)] hover:bg-[var(--accent-hover)] hover:shadow-[var(--accent-glow)] hover:-translate-y-px',
        variant === 'ghost' &&
          'bg-transparent text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]',
        variant === 'premium' &&
          'border border-[var(--border)] bg-[var(--surface)] text-[var(--text-2)] hover:border-[var(--border-strong)] hover:text-[var(--text)] hover:bg-[var(--surface-2)]',
        variant === 'danger' &&
          'bg-[var(--red-bg)] text-[var(--red)] hover:bg-[var(--red-border)]',
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
