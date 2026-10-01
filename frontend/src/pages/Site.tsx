import { BatteryCharging, Cable, Sun, Wind } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { PageLayout } from '@/components/PageLayout'
import { ErrorView, LoadingView } from '@/components/StateViews'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { useAsync } from '@/hooks/useAsync'
import { api } from '@/lib/api'
import { dateTime, energy, num, pct, power } from '@/lib/format'
import type { Config, MachineConfig } from '@/lib/types'

function Spec({ icon: Icon, title, rows }: { icon: LucideIcon; title: string; rows: [string, ReactNode][] }) {
  return (
    <Card>
      <CardBody>
        <div className="mb-4 flex items-center gap-2">
          <Icon className="h-5 w-5 text-brand" aria-hidden />
          <h2 className="font-semibold text-fg">{title}</h2>
        </div>
        <dl className="space-y-2 text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4">
              <dt className="text-muted">{label}</dt>
              <dd className="tabular text-right font-mono text-fg">{value}</dd>
            </div>
          ))}
        </dl>
      </CardBody>
    </Card>
  )
}

function rule(m: MachineConfig): string {
  if (m.type === 'always_on') return 'Runs 24/7 (part of base load)'
  if (m.type === 'daily_quota') return `${m.hours_per_day} h every day`
  const due = m.due ? dateTime(m.due) : `${m.due_in_hours} h after plan start`
  const start = m.earliest_start ? `, not before ${dateTime(m.earliest_start)}` : m.start_in_hours ? `, not before +${m.start_in_hours} h` : ''
  return `${m.total_hours} h total, due ${due}${start}`
}

const TYPE_LABEL = { always_on: 'Always on', daily_quota: 'Daily quota', deadline: 'Deadline job' }

function Content({ config }: { config: Config }) {
  const { site, machines } = config
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Spec icon={Sun} title="Solar" rows={[['Peak power', `${num(site.solar.kwp)} kWp`], ['Tilt', `${site.solar.tilt}°`], ['Azimuth', `${site.solar.azimuth}° (0 = south)`], ['Performance ratio', pct(site.solar.performance_ratio)]]} />
        <Spec icon={Wind} title="Wind" rows={[['Rated power', power(site.wind.rated_kw)], ['Hub height', `${site.wind.hub_height_m} m`], ['Curve points', site.wind.power_curve.length]]} />
        <Spec icon={BatteryCharging} title="Battery" rows={[['Capacity', energy(site.battery.capacity_kwh)], ['Charge / discharge', `${power(site.battery.max_charge_kw)} / ${power(site.battery.max_discharge_kw)}`], ['Efficiency', pct(site.battery.efficiency)], ['Minimum charge', pct(site.battery.min_soc)]]} />
        <Spec icon={Cable} title="Grid" rows={[['Max import', power(site.grid.max_import_kw)], ['Max export', power(site.grid.max_export_kw)], ['Fees and levies', `€${num(site.grid.fee_eur_per_kwh, 3)}/kWh`], ['Export price', `€${num(site.grid.export_price_eur_per_kwh, 3)}/kWh`]]} />
      </div>
      <Card>
        <CardHeader title="Machines" description="Loaded from machines.yaml. Replace with the client's machine list for the pilot." />
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted">
                <th className="py-2 pr-4 font-medium">Machine</th>
                <th className="py-2 pr-4 font-medium">Type</th>
                <th className="py-2 pr-4 text-right font-medium">Power</th>
                <th className="py-2 pr-4 text-right font-medium">Min. block</th>
                <th className="py-2 font-medium">Rule</th>
              </tr>
            </thead>
            <tbody>
              {machines.map((m) => (
                <tr key={m.id} className="border-b border-border last:border-0">
                  <td className="py-2.5 pr-4 font-medium text-fg">{m.name}</td>
                  <td className="py-2.5 pr-4">
                    <Badge tone={m.type === 'always_on' ? 'neutral' : m.type === 'deadline' ? 'warning' : 'info'}>{TYPE_LABEL[m.type]}</Badge>
                  </td>
                  <td className="tabular py-2.5 pr-4 text-right font-mono text-fg">{power(m.power_kw)}</td>
                  <td className="tabular py-2.5 pr-4 text-right font-mono text-muted">{m.type === 'always_on' ? '–' : `${m.min_run_hours} h`}</td>
                  <td className="py-2.5 text-muted">{rule(m)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
      <p className="text-xs text-muted">
        {site.name} · {num(site.latitude, 2)}°N {num(site.longitude, 2)}°E · CO₂ factor {site.co2_kg_per_kwh} kg/kWh · alerts to {site.email_recipients.join(', ') || 'nobody'}
      </p>
    </div>
  )
}

export function Site() {
  const config = useAsync(api.config)
  return (
    <PageLayout title="Site & machines" subtitle="Configuration used by the planner">
      {config.loading && !config.data ? (
        <LoadingView />
      ) : config.error ? (
        <ErrorView message={config.error.message} onRetry={() => void config.reload()} />
      ) : (
        config.data && <Content config={config.data} />
      )}
    </PageLayout>
  )
}
