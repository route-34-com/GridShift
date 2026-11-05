import type { ButtonHTMLAttributes } from 'react'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'ghost'

const VARIANTS: Record<Variant, string> = {
  primary: 'btn-electric border border-transparent',
  secondary: 'border border-input bg-surface-solid text-fg shadow-[0_1px_2px_rgb(0_0_0/0.04)] hover:bg-surface-2',
  ghost: 'border border-transparent text-muted hover:bg-surface-2 hover:text-fg',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: 'sm' | 'md' | 'icon'
  /** Show a spinner in place of the button's icon and block clicks while work is in progress. */
  loading?: boolean
}

export function Button({ variant = 'secondary', size = 'md', className, type = 'button', loading = false, disabled, children, ...props }: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-[color,background-color,border-color,transform] duration-150 select-none active:translate-y-px disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0',
        size === 'sm' && 'h-8 px-2.5',
        size === 'md' && 'h-9 px-3',
        size === 'icon' && 'h-9 w-9',
        VARIANTS[variant],
        loading && '[&_svg:not([data-spinner])]:hidden',
        className,
      )}
      {...props}
    >
      {loading && <Spinner aria-hidden role={undefined} aria-label={undefined} />}
      {children}
    </button>
  )
}
