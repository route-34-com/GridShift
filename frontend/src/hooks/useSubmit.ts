import { useCallback, useState } from 'react'

export function useSubmit<A extends unknown[], R>(action: (...args: A) => Promise<R>) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = useCallback(
    async (...args: A): Promise<R | undefined> => {
      setBusy(true)
      setError(null)
      try {
        return await action(...args)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
        return undefined
      } finally {
        setBusy(false)
      }
    },
    [action],
  )

  return { submit, busy, error, setError }
}
