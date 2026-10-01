import { useCallback, useEffect, useRef, useState } from 'react'

export interface AsyncState<T> {
  data: T | null
  error: Error | null
  loading: boolean
  reload: () => Promise<void>
}

export function useAsync<T>(load: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const latest = useRef(0)

  const reload = useCallback(async () => {
    const call = ++latest.current
    setLoading(true)
    try {
      const value = await load()
      if (call === latest.current) {
        setData(value)
        setError(null)
      }
    } catch (err) {
      if (call === latest.current) setError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      if (call === latest.current) setLoading(false)
    }
  }, deps)

  useEffect(() => {
    void reload()
  }, [reload])

  return { data, error, loading, reload }
}
