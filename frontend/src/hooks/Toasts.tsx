import { CheckCircle2, X, XCircle } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Tone = 'success' | 'error'

interface Toast {
  id: number
  tone: Tone
  message: string
}

interface ToastValue {
  notify: (message: string, tone?: Tone) => void
}

const ToastContext = createContext<ToastValue | null>(null)
let counter = 0

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), [])
  const notify = useCallback(
    (message: string, tone: Tone = 'success') => {
      const id = ++counter
      setToasts((all) => [...all.slice(-3), { id, tone, message }])
      setTimeout(() => dismiss(id), tone === 'error' ? 7000 : 4000)
    },
    [dismiss],
  )
  const value = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-[min(380px,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">
        {toasts.map((toast) => {
          const Icon = toast.tone === 'success' ? CheckCircle2 : XCircle
          return (
            <div
              key={toast.id}
              role={toast.tone === 'error' ? 'alert' : 'status'}
              className={cn(
                'pointer-events-auto flex items-start gap-3 rounded-lg border bg-surface-solid px-4 py-3 text-sm shadow-lg',
                toast.tone === 'success' ? 'border-positive/30' : 'border-danger/30',
              )}
            >
              <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', toast.tone === 'success' ? 'text-positive' : 'text-danger')} aria-hidden />
              <p className="flex-1 text-fg">{toast.message}</p>
              <button type="button" onClick={() => dismiss(toast.id)} aria-label="Dismiss" className="cursor-pointer text-muted hover:text-fg">
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastValue {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used inside ToastProvider')
  return value
}
