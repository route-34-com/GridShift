import type { ReactNode } from 'react'
import { EmptyView, ErrorView, LoadingView } from '@/components/StateViews'
import { useRun, type RunData } from '@/hooks/RunContext'

export function RunGate({ children }: { children: (data: RunData) => ReactNode }) {
  const { data, loading, error, empty, running, runNow, refresh, status } = useRun()
  if (loading && !data) return <LoadingView />
  if (error && !data) return <ErrorView message={error} onRetry={() => void refresh()} />
  if (empty || !data) {
    return (
      <div className="space-y-4">
        {status?.last_failure && <ErrorView message={`The last planning run failed: ${status.last_failure.error}`} />}
        <EmptyView running={running} onRun={() => void runNow()} />
      </div>
    )
  }
  return <>{children(data)}</>
}
