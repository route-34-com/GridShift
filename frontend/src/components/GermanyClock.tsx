import { Clock } from 'lucide-react'
import { useClockCycle } from '@/hooks/useClockCycle'
import { useNow } from '@/hooks/useNow'
import { clockTime } from '@/lib/clock'
import { cn } from '@/lib/utils'

const TZ = 'Europe/Berlin'
const date = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
const zone = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, timeZoneName: 'short' })
const FORMATS = {
  '24h': new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }),
  '12h': new Intl.DateTimeFormat('en-US', { timeZone: TZ, hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true }),
}
const zoneName = (now: Date) => zone.formatToParts(now).find((p) => p.type === 'timeZoneName')?.value ?? ''

/** Live German date and time, so prices and plans can be read against the clock the market uses. */
export function GermanyClock({ compact = false, className }: { compact?: boolean; className?: string }) {
  const now = useNow()
  const [cycle, setCycle] = useClockCycle()
  if (compact) {
    return (
      <button
        type="button"
        onClick={() => setCycle(cycle === '24h' ? '12h' : '24h')}
        className={cn('tabular cursor-pointer rounded-md px-1.5 py-1  text-xs text-nav-muted hover:text-nav-fg', className)}
        aria-label={`Time in Germany, ${clockTime(now, cycle)}. Switch to ${cycle === '24h' ? '12' : '24'}-hour clock`}
      >
        DE {clockTime(now, cycle)}
      </button>
    )
  }
  return (
    <div className={cn('flex shrink-0 items-center gap-3 text-sm', className)} aria-label="Date and time in Germany">
      <Clock className="h-4 w-4 text-muted" aria-hidden />
      <span className="text-muted">Germany</span>
      <span className="tabular font-medium text-fg">{FORMATS[cycle].format(now)}</span>
      <span className="hidden text-muted 2xl:inline">{date.format(now)}</span>
      <span className="text-xs text-muted">{zoneName(now)}</span>
      <div role="radiogroup" aria-label="Clock format" className="flex rounded-md border border-border p-0.5 text-[11px] font-medium">
        {(['24h', '12h'] as const).map((c) => (
          <button
            key={c}
            type="button"
            role="radio"
            aria-checked={cycle === c}
            onClick={() => setCycle(c)}
            className={cn('cursor-pointer rounded px-1.5 py-0.5 transition-colors', cycle === c ? 'bg-surface-2 text-fg' : 'text-muted hover:text-fg')}
          >
            {c}
          </button>
        ))}
      </div>
    </div>
  )
}
