import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: ReactNode
  icon: LucideIcon
  tone?: 'brand' | 'positive' | 'solar' | 'wind' | 'neutral'
}

const ICON_TONES = {
  brand: 'bg-brand-soft text-brand',
  positive: 'bg-positive-soft text-positive',
  solar: 'bg-warning-soft text-warning',
  wind: 'bg-info-soft text-info',
  neutral: 'bg-surface-2 text-muted',
}

export function StatCard({ label, value, hint, icon: Icon, tone = 'neutral' }: StatCardProps) {
  return (
    <Card className="flex min-w-0 items-start gap-4 p-5">
      <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-md', ICON_TONES[tone])}>
        <Icon className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-muted">{label}</p>
        <p className="tabular mt-1.5 truncate font-mono text-2xl leading-none font-semibold text-fg">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
      </div>
    </Card>
  )
}
