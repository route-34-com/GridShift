import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError } from '@/lib/api'
import type { Block, DatasetInfo, Hour, RunSummary, Status, TodayHour } from '@/lib/types'

export interface RunData {
  run: RunSummary
  hourly: Hour[]
  /** Today before the plan starts, for the "now" marker; empty on older runs. */
  today: TodayHour[]
  baselineHourly: Hour[]
  blocks: Block[]
  baselineBlocks: Block[]
}

interface RunContextValue {
  data: RunData | null
  status: Status | null
  /** Sample or real data, and whether each has site data; null until loaded. */
  dataset: DatasetInfo | null
  loading: boolean
  error: string | null
  empty: boolean
  running: boolean
  runError: string | null
  lastRunAt: number | null
  refresh: () => Promise<void>
  runNow: (email?: boolean) => Promise<boolean>
  dismissRunError: () => void
}

const RunContext = createContext<RunContextValue | null>(null)

async function loadRun(): Promise<RunData> {
  const [run, hourly, blocks] = await Promise.all([api.latest(), api.hourly(), api.blocks()])
  return { run, hourly: hourly.plan, today: hourly.today ?? [], baselineHourly: hourly.baseline, blocks: blocks.plan, baselineBlocks: blocks.baseline }
}

export function RunProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<RunData | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [dataset, setDataset] = useState<DatasetInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [empty, setEmpty] = useState(false)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [lastRunAt, setLastRunAt] = useState<number | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [nextStatus, nextDataset, nextData] = await Promise.all([
        api.status().catch(() => null),
        api.dataset().catch(() => null),
        loadRun().catch((err: unknown) => {
          if (err instanceof ApiError && err.status === 404) return null
          throw err
        }),
      ])
      setStatus(nextStatus)
      setDataset(nextDataset)
      setData(nextData)
      setEmpty(nextData === null)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  const runNow = useCallback(
    async (email = false) => {
      setRunning(true)
      setRunError(null)
      try {
        await api.run(email)
        setLastRunAt(Date.now())
        await refresh()
        return true
      } catch (err) {
        setRunError(err instanceof Error ? err.message : String(err))
        await refresh()
        return false
      } finally {
        setRunning(false)
      }
    },
    [refresh],
  )

  useEffect(() => {
    void refresh()
  }, [refresh])

  const value = useMemo(
    () => ({
      data,
      status,
      dataset,
      loading,
      error,
      empty,
      running: running || Boolean(status?.running),
      runError,
      lastRunAt,
      refresh,
      runNow,
      dismissRunError: () => setRunError(null),
    }),
    [data, status, dataset, loading, error, empty, running, runError, lastRunAt, refresh, runNow],
  )

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>
}

export function useRun(): RunContextValue {
  const value = useContext(RunContext)
  if (!value) throw new Error('useRun must be used inside RunProvider')
  return value
}
