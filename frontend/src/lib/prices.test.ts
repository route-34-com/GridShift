import { describe, expect, it } from 'vitest'
import { countdown, priceCoverage } from './prices'
import type { Hour } from './types'

/** 48 hours from Tuesday 6 Oct 00:00 Berlin (22:00 UTC the day before); the first `real` are published. */
function plan(real: number): Hour[] {
  const start = Date.parse('2026-10-05T22:00:00Z')
  return Array.from({ length: 48 }, (_, i) => ({ ts: new Date(start + i * 3_600_000).toISOString(), price: 90, price_source: i < real ? 'actual' : 'estimate' }) as Hour)
}

describe('priceCoverage', () => {
  it('before 13:00 the next prices are for tomorrow, out today', () => {
    const c = priceCoverage(plan(0), new Date('2026-10-05T08:00:00Z'))
    expect(c.publishedThrough).toBe('2026-10-05')
    expect(c.next).toEqual({ at: new Date('2026-10-05T11:00:00Z'), day: '2026-10-06' })
    expect(c.stale).toBe(false)
  })

  it('after 13:00 a plan without tomorrow’s real prices is stale', () => {
    const c = priceCoverage(plan(0), new Date('2026-10-05T13:30:00Z'))
    expect(c.publishedThrough).toBe('2026-10-06')
    expect(c.stale).toBe(true)
    expect(c.realUntil).toBeNull()
  })

  it('reports real prices until the end of tomorrow and the next release', () => {
    const c = priceCoverage(plan(24), new Date('2026-10-05T13:30:00Z'))
    expect(c.stale).toBe(false)
    expect(c.realUntil).toBe('2026-10-06T22:00:00.000Z')
    expect(c.days.map((d) => [d.day, d.real])).toEqual([
      ['2026-10-06', 24],
      ['2026-10-07', 0],
    ])
    expect(c.next).toEqual({ at: new Date('2026-10-06T11:00:00Z'), day: '2026-10-07' })
  })

  it('uses winter time in December', () => {
    expect(priceCoverage([], new Date('2026-12-01T09:00:00Z')).next.at).toEqual(new Date('2026-12-01T12:00:00Z'))
  })
})

it('formats a countdown', () => {
  expect(countdown(new Date(0), new Date(135 * 60_000))).toBe('2 h 15 min')
  expect(countdown(new Date(0), new Date(9 * 60_000))).toBe('9 min')
})
