import { useSyncExternalStore } from 'react'
import { readCycle, setCycle, subscribeCycle, type Cycle } from '@/lib/clock'

export function useClockCycle(): [Cycle, (c: Cycle) => void] {
  return [useSyncExternalStore(subscribeCycle, readCycle, readCycle), setCycle]
}
