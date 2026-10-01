import { Tooltip } from '@/components/ui/tooltip'
import { dayLabel, energy, localHour, num, pct, power, time } from '@/lib/format'
import type { Block, Hour, MachineSummary } from '@/lib/types'
import { machineColor } from '@/lib/utils'

interface ScheduleGanttProps {
  hours: Hour[]
  blocks: Block[]
  machines: MachineSummary[]
}

function priceColor(price: number, low: number, high: number): string {
  const ratio = high > low ? Math.min(1, Math.max(0, (price - low) / (high - low))) : 0.5
  const hue = 145 - ratio * 145
  return `hsl(${hue} 70% 45% / 0.85)`
}

function percentile(values: number[], p: number): number {
  const sorted = [...values].sort((a, b) => a - b)
  return sorted[Math.min(sorted.length - 1, Math.floor(p * sorted.length))] ?? 0
}

export function ScheduleGantt({ hours, blocks, machines }: ScheduleGanttProps) {
  if (!hours.length) return null
  const t0 = new Date(hours[0].ts).getTime()
  const span = hours.length * 3600_000
  const position = (iso: string) => ((new Date(iso).getTime() - t0) / span) * 100
  const prices = hours.map((h) => h.price)
  const low = percentile(prices, 0.05)
  const high = percentile(prices, 0.95)
  const days = hours.map((h, i) => ({ h, i })).filter(({ h }) => localHour(h.ts) === 0)
  const rows = machines.filter((m) => m.type !== 'always_on')
  const renewable = hours.map((h) => h.solar + h.wind)
  const peak = Math.max(1, ...renewable)

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[860px]">
        <div className="grid grid-cols-[168px_1fr] items-end">
          <div />
          <div className="relative h-6">
            {days.map(({ h, i }) => (
              <span key={h.ts} className="absolute top-0 text-xs font-medium text-muted" style={{ left: `${(i / hours.length) * 100}%` }}>
                <span className="pl-1.5">{dayLabel(h.ts)}</span>
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-[168px_1fr] items-center gap-y-1.5">
          <div className="pr-3 text-xs text-muted">Grid price</div>
          <div className="flex h-5 overflow-hidden rounded" role="img" aria-label="Hourly grid price from cheap (green) to expensive (red)">
            {hours.map((h) => (
              <span
                key={h.ts}
                title={`${dayLabel(h.ts)} ${time(h.ts)} · €${num(h.price, 1)}/MWh${h.price_source === 'estimate' ? ' (estimate)' : ''}`}
                className="h-full flex-1"
                style={{ background: priceColor(h.price, low, high), opacity: h.price_source === 'estimate' ? 0.6 : 1 }}
              />
            ))}
          </div>
          <div className="pr-3 text-xs text-muted">Solar + wind</div>
          <div className="flex h-5 items-end overflow-hidden rounded bg-surface-2" role="img" aria-label="Hourly on-site renewable output">
            {renewable.map((value, i) => (
              <span key={hours[i].ts} className="flex-1 bg-solar" style={{ height: `${(value / peak) * 100}%`, opacity: 0.8 }} />
            ))}
          </div>
        </div>

        <div className="relative mt-3 grid grid-cols-[168px_1fr] gap-y-2">
          {rows.map((machine, index) => {
            const own = blocks.filter((b) => b.machine_id === machine.id)
            return (
              <div key={machine.id} className="contents">
                <div className="flex min-w-0 flex-col justify-center pr-3">
                  <span className="truncate text-sm font-medium text-fg">{machine.name}</span>
                  <span className="text-xs text-muted">
                    {power(machine.power_kw)} · {machine.type === 'deadline' ? 'deadline job' : 'daily quota'}
                  </span>
                </div>
                <div className="relative h-10 rounded-md bg-surface-2">
                  {days.slice(1).map(({ h, i }) => (
                    <span key={h.ts} aria-hidden className="absolute top-0 bottom-0 w-px bg-border" style={{ left: `${(i / hours.length) * 100}%` }} />
                  ))}
                  {own.map((block) => (
                    <Tooltip
                      key={block.start}
                      content={
                        <div className="space-y-1">
                          <p className="font-medium">{block.machine_name}</p>
                          <p className="text-muted">
                            {dayLabel(block.start)} {time(block.start)}–{time(block.end)} · {block.hours} h · {energy(block.energy_kwh)}
                          </p>
                          <p>{block.reason.split(': ').slice(1).join(': ')}</p>
                          <p className="text-muted">
                            Avg €{num(block.avg_price, 0)}/MWh · {pct(block.renewable_share)} on-site renewables
                          </p>
                        </div>
                      }
                    >
                      <button
                        type="button"
                        aria-label={`${block.machine_name} ${dayLabel(block.start)} ${time(block.start)} to ${time(block.end)}`}
                        className="absolute top-1.5 bottom-1.5 cursor-pointer rounded-[5px] transition-opacity duration-150 hover:opacity-80"
                        style={{
                          left: `${position(block.start)}%`,
                          width: `max(4px, ${position(block.end) - position(block.start)}%)`,
                          background: machineColor(index),
                        }}
                      />
                    </Tooltip>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
