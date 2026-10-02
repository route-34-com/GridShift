import { Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { ErrorView } from '@/components/StateViews'
import { useAuth } from '@/hooks/AuthContext'
import { RunProvider } from '@/hooks/RunContext'

function Splash() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-bg" role="status" aria-label="Loading">
      <Loader2 className="h-6 w-6 animate-spin text-muted" aria-hidden />
    </div>
  )
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, setup, loading, error, refresh } = useAuth()
  const location = useLocation()
  if (loading && !me) return <Splash />
  if (error && !me)
    return (
      <div className="flex min-h-screen items-center bg-bg px-4">
        <ErrorView message={error} onRetry={() => void refresh()} />
      </div>
    )
  if (setup?.needed) return <Navigate to="/setup" replace />
  if (!me) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <RunProvider>{children}</RunProvider>
}

export function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth()
  if (!can(permission)) return <Navigate to="/" replace />
  return <>{children}</>
}

export function PublicOnly({ children }: { children: ReactNode }) {
  const { loading, me } = useAuth()
  if (loading && !me) return <Splash />
  return <>{children}</>
}
