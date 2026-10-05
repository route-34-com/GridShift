import { ChartCard } from '@/components/ChartCard'
import { PlanExportMenu } from '@/components/ExportMenu'
import { BatteryChart } from '@/components/charts/BatteryChart'
import { EnergyChart } from '@/components/charts/EnergyChart'
import { PriceChart } from '@/components/charts/PriceChart'
import { SunlightChart, WindChart } from '@/components/charts/WeatherCharts'
import { PageLayout } from '@/components/PageLayout'
import { Card, CardBody } from '@/components/ui/card'
import { RunGate } from '@/components/RunGate'
import { SourceBadges } from '@/components/SourceBadges'
import { useAsync } from '@/hooks/useAsync'
import { api, exportsApi } from '@/lib/api'
import { energy, num } from '@/lib/format'
import type { Config, Hour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { CLOUD_COLOR, turbineMarks } from '@/lib/weather'

function totals(hours: Hour[]) {
  const sum = (key: keyof Hour) => hours.reduce((acc, h) => acc + (h[key] as number), 0)
  return { solar: sum('solar'), wind: sum('wind'), charge: sum('charge'), discharge: sum('discharge') }
}

function mean(values: (number | null | undefined)[]): number | null {
  const known = values.filter((v): v is number => v != null)
  return known.length ? known.reduce((a, b) => a + b, 0) / known.length : null
}

function Weather({ hours, config }: { hours: Hour[]; config: Config | undefined }) {
  if (hours.every((h) => h.sunlight_w_m2 == null)) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-muted">Sunlight and wind forecasts appear here after the next re-plan.</p>
        </CardBody>
      </Card>
    )
  }
  const wind = config?.site.wind
  const marks = wind ? turbineMarks(wind.power_curve, wind.rated_kw) : null
  const sunniest = Math.max(...hours.map((h) => h.sunlight_w_m2 ?? 0))
  const clouds = mean(hours.map((h) => h.cloud_cover_pct))
  const speeds = hours.map((h) => h.wind_ms ?? 0)
  const turning = marks ? speeds.filter((s) => s > marks.startsAt && (marks.stopsAt == null || s <= marks.stopsAt)).length : 0
  const windText = marks
    ? `Wind speed at the ${num(wind!.hub_height_m)} m hub. The turbine turns from ${num(marks.startsAt)} m/s${marks.fullAt != null ? ` and gives full power from ${num(marks.fullAt)} m/s` : ''}; ${turning} of ${hours.length} h are windy enough.`
    : `Wind speed at ${num(wind?.hub_height_m ?? 100)} m, up to ${num(Math.max(...speeds), 1)} m/s. No wind turbine is configured, so it doesn't change the plan.`
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <ChartCard
        title="Sunlight"
        description={`Sunlight reaching the panels in W/m² (about 1,000 is full summer sun). Brightest hour ${num(sunniest)} W/m²${clouds != null ? `, ${num(clouds)}% cloud cover on average` : ''}.`}
        legend={[
          { label: 'Sunlight on panels', color: SERIES.solar },
          ...(clouds != null ? [{ label: 'Cloud cover', color: CLOUD_COLOR, dashed: true }] : []),
        ]}
        height={240}
      >
        <SunlightChart hours={hours} />
      </ChartCard>
      <ChartCard title="Wind" description={windText} legend={[{ label: 'Wind speed (m/s)', color: SERIES.wind }]} height={240}>
        <WindChart hours={hours} marks={marks} />
      </ChartCard>
    </div>
  )
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
      <Weather hours={hours} config={config.data ?? undefined} />
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
      subtitle="Hourly prices, weather, solar and wind output, factory load and battery plan"
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
