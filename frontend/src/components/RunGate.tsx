import type { ReactNode } from 'react'
import { EmptyView, ErrorView, LoadingView, NoRealDataView } from '@/components/StateViews'
import { useAuth } from '@/hooks/AuthContext'
import { useRun, type RunData } from '@/hooks/RunContext'
import { api } from '@/lib/api'

export function RunGate({ children }: { children: (data: RunData) => ReactNode }) {
  const { data, loading, error, empty, running, runNow, refresh, status, dataset } = useRun()
  const { can } = useAuth()
  if (loading && !data) return <LoadingView />
  if (error && !data) return <ErrorView message={error} onRetry={() => void refresh()} />
  if (empty || !data) {
    if (dataset?.active === 'live' && !dataset.live.available && dataset.switchable) {
      const useSample = () => void api.setDataset('sample').then(() => window.location.reload())
      return <NoRealDataView canSwitch={can('data.switch')} onUseSample={useSample} />
    }
    return (
      <div className="space-y-4">
        {status?.last_failure && <ErrorView message={`The last planning run failed: ${status.last_failure.error}`} />}
        <EmptyView running={running} onRun={() => void runNow()} />
      </div>
    )
  }
  return <>{children(data)}</>
}
