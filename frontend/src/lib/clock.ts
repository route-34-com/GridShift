/** The viewer's 12/24-hour preference, shared by the Germany clock and chart labels. */
export type Cycle = '24h' | '12h'

const KEY = 'gridshift-clock'
const TZ = 'Europe/Berlin'
const listeners = new Set<() => void>()

export function getCycle(): Cycle {
  try {
    return localStorage.getItem(KEY) === '12h' ? '12h' : '24h'
  } catch {
    return '24h'
  }
}

let current: Cycle = getCycle()

export function readCycle(): Cycle {
  return current
}

export function setCycle(next: Cycle): void {
  current = next
  try {
    localStorage.setItem(KEY, next)
  } catch {
    // Private mode: keep the choice for this visit only.
  }
  listeners.forEach((l) => l())
}

export function subscribeCycle(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

const SHORT = {
  '24h': new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }),
  '12h': new Intl.DateTimeFormat('en-US', { timeZone: TZ, hour: 'numeric', minute: '2-digit', hour12: true }),
}

/** German wall-clock time as "16:15" or "4:15 PM". */
export const clockTime = (date: Date, cycle: Cycle) => SHORT[cycle].format(date)
