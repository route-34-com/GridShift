import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { auth, onUnauthorized } from '@/lib/api'
import type { Me, SetupStatus } from '@/lib/types'

interface AuthValue {
  me: Me | null
  setup: SetupStatus | null
  loading: boolean
  error: string | null
  signIn: (me: Me) => void
  signOut: () => Promise<void>
  refresh: () => Promise<void>
  can: (permission: string) => boolean
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [setup, setSetup] = useState<SetupStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const status = await auth.setupStatus()
      setSetup(status)
      setMe(status.needed ? null : await auth.me().catch(() => null))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => onUnauthorized(() => setMe(null)), [])

  const signOut = useCallback(async () => {
    await auth.logout().catch(() => null)
    setMe(null)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      me,
      setup,
      loading,
      error,
      signIn: (next) => {
        setMe(next)
        setSetup((s) => (s ? { ...s, needed: false } : s))
      },
      signOut,
      refresh,
      can: (permission) => Boolean(me?.permissions.includes(permission)),
    }),
    [me, setup, loading, error, signOut, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}
