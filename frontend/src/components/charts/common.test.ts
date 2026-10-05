import { describe, expect, it } from 'vitest'
import { HOUR, nowLine, splitAtNow, type Row } from './common'

const start = Date.parse('2026-10-05T22:00:00Z')
const rows: Row[] = [0, 1, 2, 3].map((i) => ({ t: start + i * HOUR, v: 10 + i }))

describe('now marker', () => {
  it('greys finished hours and keeps the line joined at the current hour', () => {
    const split = splitAtNow(rows, 'v', start + 1.5 * HOUR)
    expect(split.map((r) => r.vPast)).toEqual([10, 11, null, null])
    expect(split.map((r) => r.vNext)).toEqual([null, 11, 12, 13])
  })

  it('draws the line only when now is on the chart', () => {
    expect(nowLine(rows, start + 2 * HOUR, 'Now')?.x).toBe(start + 2 * HOUR)
    expect(nowLine(rows, start - HOUR, 'Now')).toBeNull()
    expect(nowLine(rows, start + 5 * HOUR, 'Now')).toBeNull()
  })
})
