import type { ReactNode } from 'react'
import { dateTime, localHour, time, weekday } from '@/lib/format'

export interface Row {
  t: number
  [key: string]: number | null
}

type Timed = { ts: string }

export function toRows<T extends Timed>(hours: T[], map: (h: T, i: number) => Record<string, number | null>): Row[] {
  return hours.map((h, i) => ({ t: new Date(h.ts).getTime(), ...map(h, i) }))
}

/** Up to a day gets a tick every 3 hours, two days every 6 hours; longer spans one per day. */
function tickStep(hours: Timed[]): number {
  return hours.length <= 30 ? 3 : hours.length <= 50 ? 6 : 24
}

export function dayTicks(hours: Timed[]): number[] {
  const step = tickStep(hours)
  return hours.filter((h) => localHour(h.ts) % step === 0).map((h) => new Date(h.ts).getTime())
}

export const tickWeekday = (t: number) => weekday(new Date(t).toISOString())
export const tickTime = (t: number) => time(new Date(t).toISOString())

export const axisProps = {
  tickLine: false,
  axisLine: false,
  tick: { fontSize: 12 },
} as const

export const xAxisProps = (hours: Timed[]) => ({
  ...axisProps,
  dataKey: 't',
  type: 'number' as const,
  scale: 'time' as const,
  domain: ['dataMin', 'dataMax'] as [string, string],
  ticks: dayTicks(hours),
  tickFormatter: tickStep(hours) < 24 ? (t: number) => (localHour(new Date(t).toISOString()) === 0 ? tickWeekday(t) : tickTime(t)) : tickWeekday,
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

/** An hour is past once it has fully ended. */
export const HOUR = 3_600_000
export const isPast = (t: number, now: number) => t + HOUR <= now

/**
 * Split one series into past (grey) and coming (coloured) parts that meet at the current hour,
 * so the line stays continuous across the "now" marker.
 */
export function splitAtNow(rows: Row[], key: string, now: number): Row[] {
  const firstFuture = rows.findIndex((r) => !isPast(r.t, now))
  return rows.map((r, i) => {
    const past = isPast(r.t, now) || i === firstFuture
    const coming = !isPast(r.t, now)
    return { ...r, [`${key}Past`]: past ? r[key] : null, [`${key}Next`]: coming ? r[key] : null }
  })
}

/** Props for the vertical "Now" line; null when now is outside the chart. */
export function nowLine(rows: Row[], now: number, label: string) {
  if (!rows.length || now < rows[0].t || now > rows[rows.length - 1].t + HOUR) return null
  return {
    x: Math.min(now, rows[rows.length - 1].t),
    stroke: 'var(--fg)',
    strokeWidth: 1.5,
    ifOverflow: 'extendDomain' as const,
    label: { value: label, position: 'insideTopRight' as const, fontSize: 11, fontWeight: 600, fill: 'var(--fg)', offset: 6 },
  }
}

export const PAST_COLOR = 'var(--series-baseline)'
