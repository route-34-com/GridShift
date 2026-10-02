import { ChartCard } from '@/components/ChartCard'
import { PlanExportMenu } from '@/components/ExportMenu'
import { BatteryChart } from '@/components/charts/BatteryChart'
import { EnergyChart } from '@/components/charts/EnergyChart'
import { PriceChart } from '@/components/charts/PriceChart'
import { PageLayout } from '@/components/PageLayout'
import { RunGate } from '@/components/RunGate'
import { SourceBadges } from '@/components/SourceBadges'
import { useAsync } from '@/hooks/useAsync'
import { api, exportsApi } from '@/lib/api'
import { energy, num } from '@/lib/format'
import type { Hour } from '@/lib/types'
import { SERIES } from '@/lib/utils'

function totals(hours: Hour[]) {
  const sum = (key: keyof Hour) => hours.reduce((acc, h) => acc + (h[key] as number), 0)
  return { solar: sum('solar'), wind: sum('wind'), charge: sum('charge'), discharge: sum('discharge') }
}

function Content({ hours, sources }: { hours: Hour[]; sources: Record<string, string> }) {
  const config = useAsync(api.config)
  const capacity = config.data?.site.battery.capacity_kwh ?? Math.max(...hours.map((h) => h.soc), 1)
  const t = totals(hours)
  const prices = hours.map((h) => h.price)
  const negative = prices.filter((p) => p < 0).length
  return (
    <div className="space-y-6">
      <SourceBadges sources={sources} />
      <ChartCard
        title="Grid price"
        description={
          <>
            Day-ahead price in €/MWh. Range €{num(Math.min(...prices))} to €{num(Math.max(...prices))}
            {negative > 0 && `, ${negative} h below zero`}.
          </>
        }
        legend={[
          { label: 'Published', color: SERIES.price },
          { label: 'Estimated from weather', color: SERIES.price, dashed: true },
        ]}
        height={260}
      >
        <PriceChart hours={hours} />
      </ChartCard>
      <ChartCard
        title="On-site generation and factory load"
        description={`Solar ${energy(t.solar)} and wind ${energy(t.wind)} expected over the week`}
        legend={[
          { label: 'Wind', color: SERIES.wind },
          { label: 'Solar', color: SERIES.solar },
          { label: 'Planned factory load', color: SERIES.demand },
          { label: 'Base load', color: SERIES.baseline, dashed: true },
        ]}
        height={300}
      >
        <EnergyChart hours={hours} />
      </ChartCard>
      <ChartCard
        title="Battery"
        description={`Charges ${energy(t.charge)} and discharges ${energy(t.discharge)} over the week`}
        legend={[
          { label: 'State of charge', color: SERIES.battery },
          { label: 'Charging', color: 'var(--positive)' },
          { label: 'Discharging', color: SERIES.price },
        ]}
        height={240}
      >
        <BatteryChart hours={hours} capacity={capacity} />
      </ChartCard>
    </div>
  )
}

export function Forecast() {
  return (
    <PageLayout
      title="Forecast"
      subtitle="Hourly prices, solar and wind output, factory load and battery plan"
      actions={
        <PlanExportMenu
          options={[
            { label: 'Hourly plan (168 hours)', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('hourly', f) },
            { label: 'Hourly run-as-needed baseline', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('baseline-hourly', f) },
          ]}
        />
      }
    >
      <RunGate>{({ hourly, run }) => <Content hours={hourly} sources={run.sources} />}</RunGate>
    </PageLayout>
  )
}
