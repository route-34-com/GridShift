import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { CountUp } from '@/components/CountUp'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon: LucideIcon
  tone?: 'brand' | 'positive' | 'solar' | 'wind' | 'neutral'
  /** The page's headline figure: gradient type. */
  highlight?: boolean
}

const ICON_TONES = {
  brand: 'bg-brand-soft text-brand shadow-[0_0_20px_-6px_var(--brand)]',
  positive: 'bg-positive-soft text-positive shadow-[0_0_20px_-6px_var(--positive)]',
  solar: 'bg-warning-soft text-warning shadow-[0_0_20px_-6px_var(--warning)]',
  wind: 'bg-info-soft text-info shadow-[0_0_20px_-6px_var(--info)]',
  neutral: 'bg-surface-2 text-muted',
}

export function StatCard({ label, value, hint, icon: Icon, tone = 'neutral', highlight = false }: StatCardProps) {
  return (
    <div className="edge flex min-w-0 items-start gap-4 rounded-xl p-5 shadow-(--shadow) transition-shadow duration-300 hover:shadow-(--glow)">
      <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', ICON_TONES[tone])}>
        <Icon className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-muted">{label}</p>
        <p className={cn('tabular mt-2 truncate font-mono text-[28px] leading-none font-semibold tracking-tight', highlight ? 'text-gradient' : 'text-fg')}>
          {typeof value === 'string' ? <CountUp text={value} /> : value}
        </p>
        {hint && <p className="mt-2 text-xs leading-relaxed text-muted">{hint}</p>}
      </div>
    </div>
  )
}
