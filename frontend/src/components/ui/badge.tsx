import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type Tone = 'neutral' | 'positive' | 'warning' | 'danger' | 'info' | 'brand'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-muted',
  positive: 'bg-positive-soft text-positive',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
  info: 'bg-info-soft text-info',
  brand: 'bg-brand-soft text-brand',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone
}

export function Badge({ tone = 'neutral', className, ...props }: BadgeProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium whitespace-nowrap', TONES[tone], className)}
      {...props}
    />
  )
}
