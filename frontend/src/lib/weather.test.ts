import { describe, expect, it } from 'vitest'
import { checkCurve, parseCurveText, turbineMarks, typicalCurve } from './weather'

const CURVE: [number, number][] = [[0, 0], [3, 0], [4, 25], [12, 790], [13, 800], [25, 800], [25.1, 0], [40, 0]]

describe('turbineMarks', () => {
  it('finds where the turbine starts, reaches full power and shuts off', () => {
    expect(turbineMarks(CURVE, 800)).toEqual({ startsAt: 3, fullAt: 13, stopsAt: 25 })
  })

  it('returns nothing without a turbine', () => {
    expect(turbineMarks(CURVE, 0)).toBeNull()
  })
})

describe('checkCurve', () => {
  it('turns rows into a curve and skips blank rows', () => {
    const rows = [{ speed: '0', kw: '0' }, { speed: '', kw: '' }, { speed: '4,5', kw: '120' }]
    expect(checkCurve(rows, 800)).toEqual({ curve: [[0, 0], [4.5, 120]], errors: {}, notes: {} })
  })

  it('flags speeds that do not go up, negative power and missing numbers', () => {
    const rows = [{ speed: '5', kw: '100' }, { speed: '5', kw: '200' }, { speed: '6', kw: '-1' }, { speed: 'x', kw: '1' }]
    expect(Object.keys(checkCurve(rows, 800).errors)).toEqual(['1', '2', '3'])
  })

  it('notes power above the rating without rejecting it', () => {
    const { curve, notes } = checkCurve([{ speed: '0', kw: '0' }, { speed: '13', kw: '900' }], 800)
    expect(curve).toHaveLength(2)
    expect(notes[1]).toMatch(/800 kW/)
  })
})

describe('parseCurveText', () => {
  it('reads tab, space and semicolon separated datasheet lines', () => {
    expect(parseCurveText('3\t0\n4 130\r\n5;370\nheader only')).toEqual([
      { speed: '3', kw: '0' },
      { speed: '4', kw: '130' },
      { speed: '5', kw: '370' },
    ])
  })
})

describe('typicalCurve', () => {
  it('scales to the rated power and has start, full and storm-stop points', () => {
    const curve = typicalCurve(4200)
    expect(turbineMarks(curve, 4200)).toEqual({ startsAt: 3, fullAt: 13, stopsAt: 25 })
    expect(Math.max(...curve.map(([, kw]) => kw))).toBe(4200)
  })
})
