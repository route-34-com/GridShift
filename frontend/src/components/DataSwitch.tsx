import { FlaskConical } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/hooks/AuthContext'
import { useRun } from '@/hooks/RunContext'
import { useToast } from '@/hooks/Toasts'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

/** Sidebar switch between the built-in Holcim sample and the company's own data. Admins only. */
export function DataSwitch() {
  const { dataset } = useRun()
  const { can } = useAuth()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  if (!dataset?.switchable) return null
  const on = dataset.active === 'sample'
  const allowed = can('data.switch')

  async function toggle() {
    setBusy(true)
    try {
      await api.setDataset(on ? 'live' : 'sample')
      // Every page reads site data, so reload once rather than refreshing each view.
      window.location.reload()
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
      setBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-nav-line bg-nav-hover p-3">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor="sample-data" className="flex items-center gap-2 text-sm font-medium text-nav-fg">
          <FlaskConical className={cn('h-4 w-4', on ? 'text-mark' : 'text-nav-muted')} aria-hidden />
          Sample data
        </label>
        <button
          id="sample-data"
          type="button"
          role="switch"
          aria-checked={on}
          disabled={!allowed || busy}
          onClick={() => void toggle()}
          title={allowed ? undefined : 'Only admins can switch'}
          className={cn(
            'relative h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-60',
            on ? 'bg-mark' : 'bg-nav-muted/35',
          )}
        >
          <span aria-hidden className={cn('absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform', on && 'translate-x-4')} />
        </button>
      </div>
      <p className="mt-1.5 text-[11px] leading-snug text-nav-muted">{on ? 'Holcim sample: illustrative figures, not real plant data.' : 'Showing your company’s own data.'}</p>
    </div>
  )
}
