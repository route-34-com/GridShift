import { useState } from 'react'
import { PlanExportMenu } from '@/components/ExportMenu'
import { PageLayout } from '@/components/PageLayout'
import { RunGate } from '@/components/RunGate'
import { ScheduleGantt } from '@/components/ScheduleGantt'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Loader } from '@/components/ui/spinner'
import type { RunData } from '@/hooks/RunContext'
import { useAsync } from '@/hooks/useAsync'
import { useNow } from '@/hooks/useNow'
import { api, exportsApi } from '@/lib/api'
import { dayLabel, energy, eur, time, timeSpan } from '@/lib/format'
import type { Block, Hour, TodayPlan } from '@/lib/types'
import { Segmented } from '@/components/ui/segmented'
import { machineColor } from '@/lib/utils'

type View = 'plan' | 'baseline'

function Toggle({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const options: { value: View; label: string }[] = [
    { value: 'plan', label: 'GridShift plan' },
    { value: 'baseline', label: 'Run-as-needed' },
  ]
  return <Segmented label="Schedule view" value={view} options={options} onChange={onChange} />
}

function BlockRow({ block, color, running = false }: { block: Block; color: string; running?: boolean }) {
  return (
    <li className="flex gap-3 text-sm">
      <span aria-hidden className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: color }} />
      <div className="min-w-0">
        <p className="text-fg">
          <span className="font-medium">{block.machine_name}</span>{' '}
          <span className="tabular whitespace-nowrap text-muted">{timeSpan(block.start, block.end)}</span>
          {running && <Badge tone="brand" className="ml-1.5">Running now</Badge>}
        </p>
        <p className="text-xs text-muted">{block.reason.split(': ').slice(1).join(': ')}</p>
      </div>
    </li>
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
              <BlockRow key={`${b.machine_id}-${b.start}`} block={b} color={machineColor(order.indexOf(b.machine_id))} />
            ))}
          </ul>
        </div>
      ))}
    </div>
  )
}

function priceNote(hours: Hour[]): { tone: 'brand' | 'warning'; text: string } {
  const estimated = hours.filter((h) => h.price_source === 'estimate').length
  if (estimated === 0) return { tone: 'brand', text: 'Published prices' }
  return { tone: 'warning', text: estimated === hours.length ? 'Estimated prices' : 'Partly estimated prices' }
}

function TodayContent({ plan }: { plan: TodayPlan }) {
  const now = useNow(60_000)
  const order = plan.run.machines.filter((m) => m.type !== 'always_on').map((m) => m.id)
  const note = priceNote(plan.hourly)
  const moment = now.getTime()
  const runningNow = (b: Block) => new Date(b.start).getTime() <= moment && moment < new Date(b.end).getTime()
  const energyToday = plan.blocks.reduce((acc, b) => acc + b.energy_kwh, 0)
  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2 text-xs">
        <Badge tone={note.tone}>{note.text}</Badge>
        <Badge>{plan.blocks.length} run blocks</Badge>
        <Badge>{energy(energyToday)} flexible energy</Badge>
      </div>
      {plan.blocks.length ? (
        <>
          <ScheduleGantt hours={plan.hourly} blocks={plan.blocks} machines={plan.run.machines} clockAxis now={now} />
          <ul className="mt-6 grid gap-x-8 gap-y-3 md:grid-cols-2 xl:grid-cols-3">
            {plan.blocks.map((b) => (
              <BlockRow key={`${b.machine_id}-${b.start}`} block={b} color={machineColor(order.indexOf(b.machine_id))} running={runningNow(b)} />
            ))}
          </ul>
        </>
      ) : (
        <p className="text-sm text-muted">No flexible machines are scheduled today.</p>
      )}
    </>
  )
}

function TodayCard({ runId }: { runId: number }) {
  const { data: plan, error, loading } = useAsync(api.todayPlan, [runId])
  const made = plan ? `Plan #${plan.run.id}, made ${dayLabel(plan.run.created_at)} at ${time(plan.run.created_at)}.` : ''
  return (
    <Card>
      <CardHeader
        title={plan ? `Today's plan · ${dayLabel(plan.hourly[0].ts)}` : "Today's plan"}
        description={plan ? `${made} The line marks the current time. Re-planning doesn't change today.` : 'What each machine runs today, in Europe/Berlin time.'}
      />
      <CardBody>
        {plan ? (
          <TodayContent plan={plan} />
        ) : loading ? (
          <Loader label="Loading today's plan…" className="min-h-28" />
        ) : (
          <p className="text-sm text-muted">
            {error
              ? "Today's plan couldn't be loaded. Refresh the page to try again."
              : 'No saved plan covers today. Each plan starts at the next midnight, so the first one shows here the day after it runs.'}
          </p>
        )}
      </CardBody>
    </Card>
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
      <TodayCard runId={data.run.id} />
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
    <PageLayout
      title="Schedule"
      subtitle="When each flexible machine runs today and over the next 7 days"
      actions={
        <PlanExportMenu
          options={[
            { label: 'GridShift schedule', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('schedule', f) },
            { label: 'Run-as-needed schedule', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('baseline-schedule', f) },
          ]}
        />
      }
    >
      <RunGate>{(data) => <Content data={data} />}</RunGate>
    </PageLayout>
  )
}
