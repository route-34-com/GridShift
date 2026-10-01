import { AlertOctagon, AlertTriangle, Info } from 'lucide-react'
import type { Alert } from '@/lib/types'
import { cn } from '@/lib/utils'

const STYLE = {
  error: { icon: AlertOctagon, className: 'border-danger/30 bg-danger-soft text-danger' },
  warning: { icon: AlertTriangle, className: 'border-warning/30 bg-warning-soft text-warning' },
  info: { icon: Info, className: 'border-info/30 bg-info-soft text-info' },
}

export function AlertList({ alerts, warnings = [] }: { alerts: Alert[]; warnings?: string[] }) {
  const items = [...alerts, ...warnings.map((message) => ({ kind: 'note', level: 'info' as const, message }))]
  if (!items.length) return null
  return (
    <ul className="space-y-2" aria-label="Alerts">
      {items.map((alert, i) => {
        const { icon: Icon, className } = STYLE[alert.level]
        return (
          <li key={`${alert.kind}-${i}`} className={cn('flex items-start gap-3 rounded-lg border px-4 py-3 text-sm', className)}>
            <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span className="text-fg">{alert.message}</span>
          </li>
        )
      })}
    </ul>
  )
}
