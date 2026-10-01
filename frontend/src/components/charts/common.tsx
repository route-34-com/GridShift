import type { ReactNode } from 'react'
import { dateTime, localHour, weekday } from '@/lib/format'
import type { Hour } from '@/lib/types'

export interface Row {
  t: number
  [key: string]: number | null
}

export function toRows(hours: Hour[], map: (h: Hour, i: number) => Record<string, number | null>): Row[] {
  return hours.map((h, i) => ({ t: new Date(h.ts).getTime(), ...map(h, i) }))
}

export function dayTicks(hours: Hour[]): number[] {
  return hours.filter((h) => localHour(h.ts) === 0).map((h) => new Date(h.ts).getTime())
}

export const tickWeekday = (t: number) => weekday(new Date(t).toISOString())

export const axisProps = {
  tickLine: false,
  axisLine: false,
  tick: { fontSize: 12 },
} as const

export const xAxisProps = (hours: Hour[]) => ({
  ...axisProps,
  dataKey: 't',
  type: 'number' as const,
  scale: 'time' as const,
  domain: ['dataMin', 'dataMax'] as [string, string],
  ticks: dayTicks(hours),
  tickFormatter: tickWeekday,
  minTickGap: 8,
})

export interface TooltipLine {
  label: string
  color: string
  value: string
}

export function TooltipBox({ title, lines, footer }: { title: string; lines: TooltipLine[]; footer?: ReactNode }) {
  return (
    <div className="min-w-44 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="mb-1.5 font-medium text-fg">{title}</p>
      <ul className="space-y-1">
        {lines.map((line) => (
          <li key={line.label} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted">
              <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: line.color }} />
              {line.label}
            </span>
            <span className="tabular font-mono text-fg">{line.value}</span>
          </li>
        ))}
      </ul>
      {footer && <p className="mt-1.5 border-t border-border pt-1.5 text-muted">{footer}</p>}
    </div>
  )
}

export function hourTitle(t: number): string {
  return dateTime(new Date(t).toISOString())
}

export interface TooltipArgs {
  active?: boolean
  label?: number | string
  payload?: readonly { payload?: Row }[]
}

export function activeRow(args: TooltipArgs): Row | null {
  if (!args.active || !args.payload?.length) return null
  return args.payload[0].payload ?? null
}
