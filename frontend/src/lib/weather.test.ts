import { describe, expect, it } from 'vitest'
import { turbineMarks } from './weather'

const CURVE: [number, number][] = [[0, 0], [3, 0], [4, 25], [12, 790], [13, 800], [25, 800], [25.1, 0], [40, 0]]

describe('turbineMarks', () => {
  it('finds where the turbine starts, reaches full power and shuts off', () => {
    expect(turbineMarks(CURVE, 800)).toEqual({ startsAt: 3, fullAt: 13, stopsAt: 25 })
  })

  it('returns nothing without a turbine', () => {
    expect(turbineMarks(CURVE, 0)).toBeNull()
  })
})
