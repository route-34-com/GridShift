import type { ChartHour } from './types'

type Priced = Pick<ChartHour, 'ts' | 'price_source'>

const TZ = 'Europe/Berlin'
/** EPEX publishes the next day's German prices shortly before 13:00 Berlin time. */
export const PUBLISH_HOUR = 13

function berlinParts(date: Date) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-GB', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(date)
      .map((p) => [p.type, p.value]),
  )
  return { y: +parts.year, m: +parts.month, d: +parts.day, h: +parts.hour, min: +parts.minute }
}

/** Berlin calendar date as YYYY-MM-DD. */
export function berlinDay(date: Date): string {
  const { y, m, d } = berlinParts(date)
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

export function addDays(day: string, n: number): string {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10)
}

/** The instant a Berlin wall-clock time happens. */
function berlinInstant(day: string, hour: number): Date {
  const [y, m, d] = day.split('-').map(Number)
  const guess = new Date(Date.UTC(y, m - 1, d, hour))
  const seen = berlinParts(guess)
  const offset = Date.UTC(seen.y, seen.m - 1, seen.d, seen.h, seen.min) - guess.getTime()
  return new Date(guess.getTime() - offset)
}

/** An ISO time near midday of a Berlin day, safe to pass to date formatters. */
export const dayIso = (day: string) => berlinInstant(day, 12).toISOString()

export interface DayCoverage {
  day: string
  real: number
  hours: number
}

export interface PriceCoverage {
  days: DayCoverage[]
  /** End of the last hour with a published price, or null when every hour is estimated. */
  realUntil: string | null
  /** Latest day whose prices are already published on the market right now. */
  publishedThrough: string
  /** When the next day's prices come out, and which day they are for. */
  next: { at: Date; day: string }
  /** Prices are out for a day this plan still estimates: re-planning would fetch them. */
  stale: boolean
  today: string
}

export function priceCoverage(hours: Priced[], now: Date): PriceCoverage {
  const byDay = new Map<string, DayCoverage>()
  let lastReal: Priced | null = null
  for (const h of hours) {
    const day = berlinDay(new Date(h.ts))
    const entry = byDay.get(day) ?? { day, real: 0, hours: 0 }
    entry.hours += 1
    if (h.price_source === 'actual') {
      entry.real += 1
      lastReal = h
    }
    byDay.set(day, entry)
  }
  const today = berlinDay(now)
  const afterPublish = berlinParts(now).h >= PUBLISH_HOUR
  const publishedThrough = afterPublish ? addDays(today, 1) : today
  const nextDay = addDays(publishedThrough, 1)
  const at = berlinInstant(afterPublish ? addDays(today, 1) : today, PUBLISH_HOUR)
  const planned = byDay.get(publishedThrough)
  return {
    days: [...byDay.values()],
    realUntil: lastReal ? new Date(new Date(lastReal.ts).getTime() + 3_600_000).toISOString() : null,
    publishedThrough,
    next: { at, day: nextDay },
    stale: planned != null && planned.real < planned.hours,
    today,
  }
}

export function countdown(from: Date, to: Date): string {
  const minutes = Math.max(0, Math.round((to.getTime() - from.getTime()) / 60000))
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h} h ${m} min` : `${m} min`
}
