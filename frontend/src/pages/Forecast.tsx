import { Banknote, Sun, Wind, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChartCard, Legend, type LegendItem } from '@/components/ChartCard'
import { PlanExportMenu } from '@/components/ExportMenu'
import { BatteryChart } from '@/components/charts/BatteryChart'
import { EnergyChart } from '@/components/charts/EnergyChart'
import { PriceChart } from '@/components/charts/PriceChart'
import { SunlightChart, WindChart } from '@/components/charts/WeatherCharts'
import { PageLayout } from '@/components/PageLayout'
import { PriceCoverage } from '@/components/PriceCoverage'
import { RunGate } from '@/components/RunGate'
import { SourceBadges } from '@/components/SourceBadges'
import { Card, CardBody } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { MetricTabs, type TabItem } from '@/components/ui/tabs'
import { useRun } from '@/hooks/RunContext'
import { useAsync } from '@/hooks/useAsync'
import { api, exportsApi } from '@/lib/api'
import { dayLabel, energy, localDate, num } from '@/lib/format'
import type { Config, Hour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { CLOUD_COLOR, turbineMarks } from '@/lib/weather'

type View = 'price' | 'sunlight' | 'wind'
type Range = 'day' | 'week'

const VIEWS: View[] = ['price', 'sunlight', 'wind']
const RANGES = [
  { value: 'day', label: '1 day' },
  { value: 'week', label: '1 week' },
]

/** Tab and range live in the URL so a link opens the same view. */
function useForecastParams() {
  const [params, setParams] = useSearchParams()
  const view = (VIEWS as string[]).includes(params.get('view') ?? '') ? (params.get('view') as View) : 'price'
  const range: Range = params.get('range') === 'day' ? 'day' : 'week'
  const set = (key: string, value: string) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        next.set(key, value)
        return next
      },
      { replace: true },
    )
  return { view, range, setView: (v: View) => set('view', v), setRange: (r: Range) => set('range', r) }
}

/** The plan starts at tomorrow's midnight, so one day is tomorrow's local calendar day. */
function inRange(hours: Hour[], range: Range): Hour[] {
  if (range === 'week' || !hours.length) return hours
  const first = localDate(hours[0].ts)
  return hours.filter((h) => localDate(h.ts) === first)
}

function totals(hours: Hour[]) {
  const sum = (key: keyof Hour) => hours.reduce((acc, h) => acc + (h[key] as number), 0)
  return { solar: sum('solar'), wind: sum('wind'), charge: sum('charge'), discharge: sum('discharge') }
}

function mean(values: (number | null | undefined)[]): number | null {
  const known = values.filter((v): v is number => v != null)
  return known.length ? known.reduce((a, b) => a + b, 0) / known.length : null
}

interface Panel {
  icon: LucideIcon
  label: string
  value: string | null
  color: string
  description: string
  legend: LegendItem[]
  chart: ReactNode
}

function panels(hours: Hour[], config: Config | undefined, span: string): Record<View, Panel> {
  const prices = hours.map((h) => h.price)
  const negative = prices.filter((p) => p < 0).length
  const avgPrice = mean(prices) ?? 0
  const hasWeather = hours.some((h) => h.sunlight_w_m2 != null)
  const wind = config?.site.wind
  const marks = wind ? turbineMarks(wind.power_curve, wind.rated_kw) : null
  const sunniest = Math.max(0, ...hours.map((h) => h.sunlight_w_m2 ?? 0))
  const clouds = mean(hours.map((h) => h.cloud_cover_pct))
  const speeds = hours.map((h) => h.wind_ms ?? 0)
  const avgWind = mean(hours.map((h) => h.wind_ms))
  const turning = marks ? speeds.filter((s) => s > marks.startsAt && (marks.stopsAt == null || s <= marks.stopsAt)).length : 0
  const noWeather = 'Sunlight and wind forecasts appear here after the next re-plan.'
  return {
    price: {
      icon: Banknote,
      label: 'Price',
      value: `avg €${num(avgPrice)}/MWh`,
      color: SERIES.price,
      description: `Day-ahead price in €/MWh ${span}. Range €${num(Math.min(...prices))} to €${num(Math.max(...prices))}${negative > 0 ? `, ${negative} h below zero` : ''}.`,
      legend: [
        { label: 'Published', color: SERIES.price },
        { label: 'Estimated from weather', color: SERIES.price, dashed: true },
      ],
      chart: <PriceChart hours={hours} />,
    },
    sunlight: {
      icon: Sun,
      label: 'Sunlight',
      value: hasWeather ? `peak ${num(sunniest)} W/m²` : null,
      color: SERIES.solar,
      description: hasWeather
        ? `Sunlight reaching the panels in W/m² (about 1,000 is full summer sun). Brightest hour ${num(sunniest)} W/m²${clouds != null ? `, ${num(clouds)}% cloud cover on average` : ''}.`
        : noWeather,
      legend: [{ label: 'Sunlight on panels', color: SERIES.solar }, ...(clouds != null ? [{ label: 'Cloud cover', color: CLOUD_COLOR, dashed: true }] : [])],
      chart: hasWeather ? <SunlightChart hours={hours} /> : null,
    },
    wind: {
      icon: Wind,
      label: 'Wind',
      value: avgWind != null ? `avg ${num(avgWind, 1)} m/s` : null,
      color: SERIES.wind,
      description: !hasWeather
        ? noWeather
        : marks
          ? `Wind speed at the ${num(wind!.hub_height_m)} m hub. The turbine turns from ${num(marks.startsAt)} m/s${marks.fullAt != null ? ` and gives full power from ${num(marks.fullAt)} m/s` : ''}; ${turning} of ${hours.length} h are windy enough.`
          : `Wind speed at ${num(wind?.hub_height_m ?? 100)} m, up to ${num(Math.max(...speeds), 1)} m/s. No wind turbine is configured, so it doesn't change the plan.`,
      legend: [{ label: 'Wind speed (m/s)', color: SERIES.wind }],
      chart: hasWeather ? <WindChart hours={hours} marks={marks} /> : null,
    },
  }
}

function Content({ all, sources, madeAt }: { all: Hour[]; sources: Record<string, string>; madeAt: string }) {
  const config = useAsync(api.config)
  const { view, range, setView } = useForecastParams()
  const hours = inRange(all, range)
  const span = range === 'day' ? 'for tomorrow' : 'over the week'
  const capacity = config.data?.site.battery.capacity_kwh ?? Math.max(...hours.map((h) => h.soc), 1)
  const t = totals(hours)
  const views = panels(hours, config.data ?? undefined, span)
  const current = views[view]
  const tabs: TabItem<View>[] = VIEWS.map((id) => ({ id, label: views[id].label, icon: views[id].icon, value: views[id].value, color: views[id].color }))
  return (
    <div className="space-y-6">
      <SourceBadges sources={sources} />
      <PriceCoverage hours={all} madeAt={madeAt} />
      <Card>
        <CardBody className="space-y-5">
          <MetricTabs label="Forecast" idPrefix="forecast" items={tabs} active={view} onChange={setView} />
          <div key={`${view}-${range}`} id="forecast-panel" role="tabpanel" aria-labelledby={`forecast-tab-${view}`} className="rise space-y-3">
            <p className="max-w-[80ch] text-sm text-muted">{current.description}</p>
            {current.chart && (
              <>
                <Legend items={current.legend} />
                <div style={{ height: 300 }} className="min-w-0">
                  {current.chart}
                </div>
              </>
            )}
          </div>
        </CardBody>
      </Card>
      <ChartCard
        title="On-site generation and factory load"
        description={`Solar ${energy(t.solar)} and wind ${energy(t.wind)} expected ${span}`}
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
        description={`Charges ${energy(t.charge)} and discharges ${energy(t.discharge)} ${span}`}
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

function RangeSelect() {
  const { range, setRange } = useForecastParams()
  return <Select aria-label="Time range" value={range} options={RANGES} onChange={(e) => setRange(e.target.value as Range)} />
}

function Subtitle() {
  const { range } = useForecastParams()
  const hours = useRun().data?.hourly ?? []
  if (!hours.length) return <>Prices, weather, on-site output and the battery plan, hour by hour.</>
  const shown = inRange(hours, range)
  return <>{range === 'day' ? `Tomorrow, ${dayLabel(shown[0].ts)}` : `${dayLabel(hours[0].ts)} to ${dayLabel(hours[hours.length - 1].ts)}`}. Prices, weather, on-site output and the battery plan, hour by hour.</>
}

export function Forecast() {
  return (
    <PageLayout
      title="Forecast"
      subtitle={<Subtitle />}
      actions={
        <>
          <RangeSelect />
          <PlanExportMenu
            options={[
              { label: 'Hourly plan (168 hours)', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('hourly', f) },
              { label: 'Hourly run-as-needed baseline', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.run('baseline-hourly', f) },
            ]}
          />
        </>
      }
    >
      <RunGate>{({ hourly, run }) => <Content all={hourly} sources={run.sources} madeAt={run.created_at} />}</RunGate>
    </PageLayout>
  )
}
