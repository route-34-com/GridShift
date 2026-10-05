import { Clock } from 'lucide-react'
import { useNow } from '@/hooks/useNow'
import { cn } from '@/lib/utils'

const TZ = 'Europe/Berlin'
const date = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
const time = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })
const zone = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, timeZoneName: 'short' })

const zoneName = (now: Date) => zone.formatToParts(now).find((p) => p.type === 'timeZoneName')?.value ?? ''

/** Live German date and time, so prices and plans can be read against the clock the market uses. */
export function GermanyClock({ compact = false, className }: { compact?: boolean; className?: string }) {
  const now = useNow()
  if (compact) {
    return (
      <span className={cn('tabular font-mono text-xs text-nav-muted', className)} aria-label="Time in Germany">
        DE {time.format(now).slice(0, 5)}
      </span>
    )
  }
  return (
    <div className={cn('rounded-xl border border-nav-line bg-nav-hover p-3', className)} aria-label="Date and time in Germany">
      <p className="flex items-center gap-1.5 text-[11px] text-nav-muted">
        <Clock className="h-3.5 w-3.5" aria-hidden /> Germany · {zoneName(now)}
      </p>
      <p className="tabular mt-1 font-mono text-xl leading-none font-semibold tracking-tight text-nav-fg">{time.format(now)}</p>
      <p className="mt-1 text-xs text-nav-muted">{date.format(now)}</p>
    </div>
  )
}
