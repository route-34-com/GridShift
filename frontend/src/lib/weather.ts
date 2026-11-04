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

export interface CurveRow {
  speed: string
  kw: string
}

export interface CurveCheck {
  curve: [number, number][]
  errors: Record<number, string>
  notes: Record<number, string>
}

/** Turn a stored power curve into editable table rows. */
export const toCurveRows = (curve: [number, number][]): CurveRow[] => curve.map(([speed, kw]) => ({ speed: String(speed), kw: String(kw) }))

const parse = (raw: string) => (raw.trim() === '' ? NaN : Number(raw.trim().replace(',', '.')))

/** Parse the editor's rows into a power curve, with a problem per row the planner would reject. */
export function checkCurve(rows: CurveRow[], ratedKw: number): CurveCheck {
  const curve: [number, number][] = []
  const errors: Record<number, string> = {}
  const notes: Record<number, string> = {}
  rows.forEach((row, i) => {
    if (row.speed.trim() === '' && row.kw.trim() === '') return
    const speed = parse(row.speed)
    const kw = parse(row.kw)
    if (!Number.isFinite(speed) || !Number.isFinite(kw)) errors[i] = 'Enter a number in both columns.'
    else if (speed < 0) errors[i] = 'Wind speed cannot be negative.'
    else if (kw < 0) errors[i] = 'Power cannot be negative.'
    else if (curve.length && speed <= curve[curve.length - 1][0]) errors[i] = `Must be faster than ${curve[curve.length - 1][0]} m/s on the row above.`
    else {
      curve.push([speed, kw])
      if (ratedKw > 0 && kw > ratedKw) notes[i] = `Above rated power; counted as ${ratedKw} kW.`
    }
  })
  return { curve, errors, notes }
}

/** Read pasted datasheet text: one "speed power" pair per line, separated by spaces, tabs or semicolons. */
export function parseCurveText(text: string): CurveRow[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim().split(/[\s;]+|,\s+/).filter(Boolean))
    .filter((cells) => cells.length >= 2 && cells.slice(0, 2).every((c) => /^-?\d+([.,]\d+)?$/.test(c)))
    .map(([speed, kw]) => ({ speed, kw }))
}

const TYPICAL: [number, number][] = [
  [0, 0], [3, 0], [4, 0.031], [5, 0.088], [6, 0.174], [7, 0.288], [8, 0.431], [9, 0.595], [10, 0.762], [11, 0.9], [12, 0.981], [13, 1], [25, 1], [25.1, 0],
]

/** A generic modern-turbine curve (starts at 3 m/s, full power at 13 m/s, storm stop at 25 m/s) scaled to a rated power. */
export function typicalCurve(ratedKw: number): [number, number][] {
  return TYPICAL.map(([speed, share]) => [speed, Math.round(share * ratedKw)])
}
