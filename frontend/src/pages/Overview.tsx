import { Gauge, PiggyBank, Receipt, Sun } from 'lucide-react'
import { AlertList } from '@/components/AlertList'
import { PlanExportMenu, type ExportOption } from '@/components/ExportMenu'
import { ChartCard } from '@/components/ChartCard'
import { DailyCostChart } from '@/components/charts/DailyCostChart'
import { PageLayout } from '@/components/PageLayout'
import { PeakPanel } from '@/components/PeakPanel'
import { PriceCoverage } from '@/components/PriceCoverage'
import { RunGate } from '@/components/RunGate'
import { SourceBadges } from '@/components/SourceBadges'
import { StatCard } from '@/components/StatCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { useAsync } from '@/hooks/useAsync'
import { useRun } from '@/hooks/RunContext'
import { api, exportsApi } from '@/lib/api'
import { dayLabel, eur, kw, mass, num, pct } from '@/lib/format'
import type { Day, MachineSummary, RunSummary } from '@/lib/types'
import { SERIES } from '@/lib/utils'

function DayCard({ day, first }: { day: Day; first: boolean }) {
  return (
    <li className="rounded-lg border border-border p-4">
      <p className="font-medium whitespace-nowrap text-fg">{day.label}</p>
      <div className="mt-1 h-5">{first ? <Badge tone="brand">Tomorrow</Badge> : day.price_estimated && <Badge>est. price</Badge>}</div>
      <p className="tabular mt-2 font-mono text-lg font-semibold text-fg">{eur(day.cost_eur)}</p>
      <p className="text-xs text-muted">
        avg €{num(day.avg_price)}/MWh · {pct(day.renewable_share)} renewable
      </p>
      <p className="mt-2 text-xs leading-relaxed text-muted">{day.outlook}</p>
    </li>
  )
}

function MachineTable({ machines }: { machines: MachineSummary[] }) {
  const flexible = machines.filter((m) => m.type !== 'always_on')
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted">
            <th className="py-2 pr-4 font-medium">Machine</th>
            <th className="py-2 pr-4 font-medium">Hours</th>
            <th className="py-2 pr-4 text-right font-medium">Avg price paid</th>
            <th className="py-2 pr-4 text-right font-medium">Run-as-needed</th>
            <th className="py-2 text-right font-medium">Difference</th>
          </tr>
        </thead>
        <tbody>
          {flexible.map((m) => {
            const diff = m.avg_price != null && m.baseline_avg_price != null ? m.avg_price - m.baseline_avg_price : null
            const short = (m.scheduled_hours ?? 0) < (m.required_hours ?? 0)
            return (
              <tr key={m.id} className="border-b border-border last:border-0">
                <td className="py-2.5 pr-4">
                  <p className="font-medium text-fg">{m.name}</p>
                  <p className="text-xs text-muted">{m.type === 'deadline' ? 'Deadline job' : 'Daily quota'}</p>
                </td>
                <td className="tabular py-2.5 pr-4 font-mono">
                  <span className={short ? 'text-danger' : 'text-fg'}>
                    {m.scheduled_hours}/{m.required_hours} h
                  </span>
                </td>
                <td className="tabular py-2.5 pr-4 text-right font-mono text-fg">{m.avg_price != null ? `€${num(m.avg_price)}` : '–'}</td>
                <td className="tabular py-2.5 pr-4 text-right font-mono text-muted">
                  {m.baseline_avg_price != null ? `€${num(m.baseline_avg_price)}` : '–'}
                </td>
                <td className="py-2.5 text-right">
                  {diff != null && (
                    <Badge tone={diff <= 0 ? 'positive' : 'warning'}>
                      {diff <= 0 ? '−' : '+'}
                      {pct(Math.abs(diff) / Math.max(1, m.baseline_avg_price ?? 1))}
                    </Badge>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-muted">Average day-ahead price in €/MWh during each machine's scheduled hours.</p>
    </div>
  )
}

function PeakCard({ optimized, baseline, peak }: Pick<RunSummary['summary'], 'optimized' | 'baseline' | 'peak'>) {
  if (!peak || peak.charge_eur_per_kw_year <= 0) {
    return <StatCard icon={Gauge} label="Highest grid draw" value={kw(optimized.peak_import_kw)} hint="No peak charge configured" />
  }
  const added = optimized.peak_charge_eur ?? 0
  const avoided = (baseline.peak_charge_eur ?? 0) - added
  const raised = added > 0
  const hint = raised
    ? `Above this year's ${kw(peak.record_kw)} record: +${eur(added)} peak charge`
    : `Under this year's ${kw(peak.record_kw)} record` + (avoided > 0 ? ` · avoids ${eur(avoided)} peak charge` : '')
  return <StatCard icon={Gauge} tone={raised ? 'solar' : 'positive'} label="Highest grid draw" value={kw(optimized.peak_import_kw)} hint={hint} />
}

function PeakSection({ run }: { run: RunSummary }) {
  const live = useAsync(api.peak)
  const { runNow, running } = useRun()
  const peak = live.data ?? run.summary.peak
  if (!peak || peak.charge_eur_per_kw_year <= 0) return null
  const planned = run.summary.peak?.record_kw
  const stale = live.data !== null && planned !== undefined && Math.abs(live.data.record_kw - planned) > 0.5
  return (
    <PeakPanel peak={peak} planHighestKw={run.summary.optimized.peak_import_kw}>
      {stale && planned !== undefined && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg bg-warning-soft p-3 text-sm text-warning">
          <span>This plan was made with a {kw(planned)} record. Re-plan to protect the new {kw(peak.record_kw)} record.</span>
          <Button size="sm" variant="primary" onClick={() => void runNow()} disabled={running}>
            {running ? 'Planning…' : 'Re-plan now'}
          </Button>
        </div>
      )}
    </PeakPanel>
  )
}

function OverviewCoverage({ madeAt }: { madeAt: string }) {
  const hours = useRun().data?.hourly
  return hours?.length ? <PriceCoverage hours={hours} madeAt={madeAt} /> : null
}

function Content({ run }: { run: RunSummary }) {
  const { optimized, baseline, savings_eur, savings_pct, peak } = run.summary
  const tomorrow = run.daily[0]
  return (
    <div className="space-y-6">
      <AlertList alerts={run.alerts} />
      <OverviewCoverage madeAt={run.created_at} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={PiggyBank} tone="positive" label="Saved this week" value={eur(savings_eur)} hint={`${pct(savings_pct, 1)} below run-as-needed (${eur(baseline.cost_eur)})`} />
        <StatCard icon={Receipt} tone="brand" label="Planned energy cost" value={eur(optimized.cost_eur)} hint={`Tomorrow ${eur(tomorrow.cost_eur)}`} />
        <PeakCard optimized={optimized} baseline={baseline} peak={peak} />
        <StatCard icon={Sun} tone="solar" label="On-site renewable share" value={pct(optimized.renewable_share)} hint={`${num(optimized.renewable_used_kwh / 1000, 1)} MWh used · ${mass(optimized.co2_avoided_kg)} CO₂ avoided`} />
      </div>

      <PeakSection run={run} />

      <div className="grid gap-6 xl:grid-cols-5">
        <ChartCard
          className="xl:col-span-3"
          title="Daily energy cost"
          description="GridShift plan vs. running every machine as early as possible"
          legend={[
            { label: 'GridShift plan', color: SERIES.brand },
            { label: 'Run-as-needed', color: SERIES.baseline },
          ]}
          height={300}
        >
          <DailyCostChart days={run.daily} />
        </ChartCard>

        <Card className="xl:col-span-2">
          <CardHeader title="Tomorrow" description={dayLabel(tomorrow.start)} />
          <CardBody className="space-y-4 pt-3 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-surface-2 p-3">
                <p className="text-xs text-muted">Planned cost</p>
                <p className="tabular font-mono text-lg font-semibold text-fg">{eur(tomorrow.cost_eur)}</p>
              </div>
              <div className="rounded-lg bg-surface-2 p-3">
                <p className="text-xs text-muted">Avg grid price</p>
                <p className="tabular font-mono text-lg font-semibold text-fg">€{num(tomorrow.avg_price)}/MWh</p>
              </div>
            </div>
            <div>
              <p className="text-xs font-medium tracking-wide text-muted uppercase">Outlook</p>
              <p className="mt-1 text-fg">{tomorrow.outlook}</p>
            </div>
            <div>
              <p className="text-xs font-medium tracking-wide text-muted uppercase">Battery</p>
              <p className="mt-1 text-fg">{tomorrow.battery_note}</p>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium tracking-wide text-muted uppercase">Data sources</p>
              <SourceBadges sources={run.sources} />
            </div>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="7-day outlook" description="Weather-driven view of the week. Prices after tomorrow are estimates." />
        <CardBody>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            {run.daily.map((day, i) => (
              <DayCard key={day.date} day={day} first={i === 0} />
            ))}
          </ul>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Price paid per machine" description="How much cheaper each flexible machine runs under the plan" />
        <CardBody>
          <MachineTable machines={run.machines} />
        </CardBody>
      </Card>

      {run.warnings.length > 0 && <AlertList alerts={[]} warnings={run.warnings} />}
    </div>
  )
}

const EXPORTS: ExportOption[] = [
  { label: 'Full plan report', formats: ['pdf', 'xlsx'], run: (f) => exportsApi.run('report', f) },
  { label: 'Daily summary', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('daily', f) },
  { label: 'Price paid per machine', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('machines', f) },
]

export function Overview() {
  return (
    <PageLayout title="Overview" subtitle="Cost, savings and renewable use for the next 7 days" actions={<PlanExportMenu options={EXPORTS} />}>
      <RunGate>{({ run }) => <Content run={run} />}</RunGate>
    </PageLayout>
  )
}
