import type { ReactNode } from 'react'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export interface LegendItem {
  label: string
  color: string
  dashed?: boolean
}

interface ChartCardProps {
  title: string
  description?: ReactNode
  action?: ReactNode
  legend?: LegendItem[]
  height?: number
  className?: string
  children: ReactNode
}

export function Legend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span
            aria-hidden
            className="inline-block h-0.5 w-4 rounded"
            style={item.dashed ? { borderTop: `2px dashed ${item.color}`, height: 0 } : { background: item.color, height: 3 }}
          />
          {item.label}
        </li>
      ))}
    </ul>
  )
}

export function ChartCard({ title, description, action, legend, height = 280, className, children }: ChartCardProps) {
  return (
    <Card className={cn('min-w-0', className)}>
      <CardHeader title={title} description={description} action={action} />
      <CardBody className="pt-3">
        {legend && (
          <div className="mb-3">
            <Legend items={legend} />
          </div>
        )}
        <div style={{ height }} className="min-w-0">
          {children}
        </div>
      </CardBody>
    </Card>
  )
}
