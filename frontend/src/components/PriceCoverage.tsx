import { RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { useAuth } from '@/hooks/AuthContext'
import { useNow } from '@/hooks/useNow'
import { useRun } from '@/hooks/RunContext'
import { dateTime, dayLabel, localHour, time, weekday } from '@/lib/format'
import { countdown, dayIso, priceCoverage } from '@/lib/prices'
import type { Hour } from '@/lib/types'
import { cn } from '@/lib/utils'

/** "Tue 06 Oct, 24:00" rather than "Wed 07 Oct, 00:00" for the end of a day. */
function endLabel(iso: string): string {
  if (localHour(iso) !== 0) return `${dayLabel(iso)}, ${time(iso)}`
  return `${dayLabel(new Date(new Date(iso).getTime() - 3_600_000).toISOString())}, 24:00`
}

export function PriceCoverage({ hours, madeAt }: { hours: Hour[]; madeAt: string }) {
  const now = useNow(30_000)
  const { runNow, running } = useRun()
  const { can } = useAuth()
  const c = priceCoverage(hours, now)
  const nextAt = c.next.at.toISOString()
  const nextWhen = `${dayLabel(nextAt)} around ${time(nextAt)}`
  return (
    <Card>
      <CardHeader
        title="Price data in this plan"
        description={
          c.realUntil
            ? `Real market prices until ${endLabel(c.realUntil)}. Later days are estimated from the weather until their prices come out.`
            : `No real prices in this plan. The price source couldn't be reached when it was made (${dateTime(madeAt)}), so every hour is estimated from the weather.`
        }
      />
      <CardBody className="space-y-4 pt-4">
        <ol className="grid grid-cols-7 gap-1.5 sm:gap-2" aria-label="Prices per day">
          {c.days.map((d) => {
            const real = d.real === d.hours
            const partial = d.real > 0 && !real
            const iso = dayIso(d.day)
            return (
              <li key={d.day} className="min-w-0">
                <div
                  className={cn('h-2 rounded-full', real ? 'bg-price' : partial ? 'bg-price/50' : 'bg-[repeating-linear-gradient(135deg,var(--border)_0_4px,transparent_4px_8px)] ring-1 ring-border ring-inset')}
                  aria-hidden
                />
                <p className="mt-2 text-xs font-medium text-fg">{weekday(iso)}</p>
                <p className="tabular font-mono text-[11px] text-muted">{dayLabel(iso).split(' ').slice(1).join(' ')}</p>
                <p className={cn('mt-0.5 text-[11px]', real ? 'text-price' : 'text-muted')}>{real ? 'Real' : partial ? 'Part real' : 'Estimate'}</p>
              </li>
            )
          })}
        </ol>
        {c.stale ? (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-warning-soft px-4 py-3 text-sm">
            <span className="text-fg">
              Prices for {dayLabel(dayIso(c.publishedThrough))} are already out. Re-plan to use them instead of estimates.
            </span>
            {can('plan.run') && (
              <Button size="sm" variant="primary" onClick={() => void runNow()} disabled={running}>
                <RefreshCw className="h-4 w-4" aria-hidden /> {running ? 'Planning…' : 'Re-plan now'}
              </Button>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted">
            Next: prices for <span className="font-medium text-fg">{dayLabel(dayIso(c.next.day))}</span> come out {nextWhen} German time, in{' '}
            <span className="tabular font-mono text-fg">{countdown(now, c.next.at)}</span>.
          </p>
        )}
      </CardBody>
    </Card>
  )
}
