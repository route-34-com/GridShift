import { useState } from 'react'
import { PageLayout } from '@/components/PageLayout'
import { RunGate } from '@/components/RunGate'
import { ScheduleGantt } from '@/components/ScheduleGantt'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import type { RunData } from '@/hooks/RunContext'
import { dayLabel, energy, eur, time } from '@/lib/format'
import type { Block } from '@/lib/types'
import { cn, machineColor } from '@/lib/utils'

type View = 'plan' | 'baseline'

function Toggle({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const options: { value: View; label: string }[] = [
    { value: 'plan', label: 'GridShift plan' },
    { value: 'baseline', label: 'Run-as-needed' },
  ]
  return (
    <div role="radiogroup" aria-label="Schedule view" className="inline-flex rounded-lg border border-border bg-surface-2 p-0.5">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={view === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-200',
            view === o.value ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function BlockList({ blocks, order }: { blocks: Block[]; order: string[] }) {
  const byDay = new Map<string, Block[]>()
  for (const block of blocks) {
    const key = dayLabel(block.start)
    byDay.set(key, [...(byDay.get(key) ?? []), block])
  }
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {[...byDay.entries()].map(([day, items]) => (
        <div key={day} className="rounded-lg border border-border p-4">
          <p className="mb-3 font-medium text-fg">{day}</p>
          <ul className="space-y-3">
            {items.map((b) => (
              <li key={`${b.machine_id}-${b.start}`} className="flex gap-3 text-sm">
                <span aria-hidden className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: machineColor(order.indexOf(b.machine_id)) }} />
                <div className="min-w-0">
                  <p className="text-fg">
                    <span className="font-medium">{b.machine_name}</span>{' '}
                    <span className="tabular font-mono text-muted">
                      {time(b.start)}–{time(b.end)}
                    </span>
                  </p>
                  <p className="text-xs text-muted">{b.reason.split(': ').slice(1).join(': ')}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function Content({ data }: { data: RunData }) {
  const [view, setView] = useState<View>('plan')
  const blocks = view === 'plan' ? data.blocks : data.baselineBlocks
  const hours = view === 'plan' ? data.hourly : data.baselineHourly
  const order = data.run.machines.filter((m) => m.type !== 'always_on').map((m) => m.id)
  const { optimized, baseline } = data.run.summary
  const flexibleEnergy = blocks.reduce((acc, b) => acc + b.energy_kwh, 0)
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Machine schedule"
          description="Hover a block to see why it was placed there. The strips show grid price and on-site renewables."
          action={<Toggle view={view} onChange={setView} />}
        />
        <CardBody>
          <div className="mb-4 flex flex-wrap gap-2 text-xs">
            <Badge tone={view === 'plan' ? 'brand' : 'neutral'}>Week cost {eur(view === 'plan' ? optimized.cost_eur : baseline.cost_eur)}</Badge>
            <Badge>{blocks.length} run blocks</Badge>
            <Badge>{energy(flexibleEnergy)} flexible energy</Badge>
          </div>
          <ScheduleGantt hours={hours} blocks={blocks} machines={data.run.machines} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Run blocks by day" description="Times in Europe/Berlin" />
        <CardBody>
          {blocks.length ? <BlockList blocks={blocks} order={order} /> : <p className="text-sm text-muted">No flexible machines are scheduled in this horizon.</p>}
        </CardBody>
      </Card>
    </div>
  )
}

export function Schedule() {
  return (
    <PageLayout title="Schedule" subtitle="When each flexible machine runs over the next 7 days">
      <RunGate>{(data) => <Content data={data} />}</RunGate>
    </PageLayout>
  )
}
