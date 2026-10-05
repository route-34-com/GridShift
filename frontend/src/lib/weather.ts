export const CLOUD_COLOR = 'var(--series-baseline)'

export interface TurbineMarks {
  startsAt: number
  fullAt: number | null
  stopsAt: number | null
}

/** Wind speeds where the turbine starts turning, reaches full power and shuts off for safety. */
export function turbineMarks(curve: [number, number][], ratedKw: number): TurbineMarks | null {
  const firstOn = curve.findIndex(([, kw]) => kw > 0)
  if (ratedKw <= 0 || firstOn < 0) return null
  const full = curve.find(([, kw]) => kw >= ratedKw)
  const off = curve.findIndex(([, kw], i) => i > firstOn && kw === 0)
  return { startsAt: curve[Math.max(firstOn - 1, 0)][0], fullAt: full ? full[0] : null, stopsAt: off > 0 ? curve[off - 1][0] : null }
}
