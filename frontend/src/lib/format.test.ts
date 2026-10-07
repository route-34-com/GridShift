import { describe, expect, it } from 'vitest'
import { energy, eur, eurShort, localHour, pct, power, relative, time } from './format'

describe('format', () => {
  it('formats euros with sensible precision', () => {
    expect(eur(15128.2)).toBe('€15,128')
    expect(eur(12.345)).toBe('€12.35')
    expect(eur(-250)).toBe('-€250')
    expect(eur(Number.NaN)).toBe('–')
    expect(eur(0)).toBe('€0')
  })

  it('switches energy and power units at 1000', () => {
    expect(energy(950)).toBe('950 kWh')
    expect(energy(25676.4)).toBe('25.7 MWh')
    expect(power(1500)).toBe('1.5 MW')
  })

  it('formats percentages', () => {
    expect(pct(0.1967, 1)).toBe('19.7%')
  })

  it('renders times in Europe/Berlin across DST', () => {
    expect(time('2026-07-01T22:00:00+00:00')).toBe('00:00')
    expect(time('2026-12-01T23:00:00+00:00')).toBe('00:00')
    expect(localHour('2026-10-25T00:00:00+00:00')).toBe(2)
    expect(localHour('2026-10-25T01:00:00+00:00')).toBe(2)
  })

  it('describes relative time', () => {
    const now = Date.parse('2026-10-01T12:00:00Z')
    expect(relative('2026-10-01T11:59:40Z', now)).toBe('just now')
    expect(relative('2026-10-01T11:15:00Z', now)).toBe('45 min ago')
    expect(relative('2026-10-01T06:00:00Z', now)).toBe('6 h ago')
  })
})

describe('eurShort', () => {
  it('shortens large chart amounts', () => {
    expect(eurShort(140000)).toBe('€140k')
    expect(eurShort(4500)).toBe('€4,500')
    expect(eurShort(2_225_300)).toBe('€2.2M')
    expect(eurShort(-140000)).toBe('-€140k')
  })
})
