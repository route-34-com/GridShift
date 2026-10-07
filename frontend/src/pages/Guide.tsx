import { Search } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { PageLayout } from '@/components/PageLayout'
import { Badge } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/field'

interface Entry {
  term: string
  meaning: string
  example?: string
  symbol?: ReactNode
  /** The symbol already shows the term, so don't repeat it. */
  symbolOnly?: boolean
}

interface Section {
  title: string
  description: string
  entries: Entry[]
}

function Line({ color, dashed = false, width = 2 }: { color: string; dashed?: boolean; width?: number }) {
  return (
    <svg width="28" height="10" aria-hidden className="shrink-0">
      <line x1="1" y1="5" x2="27" y2="5" stroke={color} strokeWidth={width} strokeDasharray={dashed ? '4 3' : undefined} strokeLinecap="round" />
    </svg>
  )
}

function Swatch({ color }: { color: string }) {
  return <span aria-hidden className="h-3 w-3 shrink-0 rounded-sm" style={{ background: color }} />
}

function Stripe({ estimate }: { estimate: boolean }) {
  return (
    <span
      aria-hidden
      className={estimate ? 'h-2 w-7 shrink-0 rounded-full bg-[repeating-linear-gradient(135deg,var(--border)_0_4px,transparent_4px_8px)] ring-1 ring-border ring-inset' : 'h-2 w-7 shrink-0 rounded-full bg-price'}
    />
  )
}

const SECTIONS: Section[] = [
  {
    title: 'Power and energy',
    description: 'Power is how fast electricity is used at one moment; energy is how much is used over time.',
    entries: [
      { term: 'kW (kilowatt)', meaning: 'Power: the rate of use or output at one moment.', example: 'A 4.2 MW mill draws 4,200 kW while it runs.' },
      { term: 'MW (megawatt)', meaning: '1,000 kW. Used for large machines and the grid connection.', example: '26,180 kW = 26.18 MW' },
      { term: 'kWh (kilowatt-hour)', meaning: 'Energy: 1 kW used for 1 hour. Electricity is billed per kWh.', example: '4,200 kW for 3 h = 12,600 kWh' },
      { term: 'MWh (megawatt-hour)', meaning: '1,000 kWh. Used for weekly totals and market prices.' },
      { term: 'kWp (kilowatt-peak)', meaning: 'Rated output of a solar array in full sun under test conditions. Real output is usually lower.' },
      { term: 'SoC (state of charge)', meaning: 'How full the battery is, from 0% (empty) to 100% (full). It never goes below the minimum charge set for the site.' },
    ],
  },
  {
    title: 'Prices and money',
    description: 'All amounts are in euros. Large chart labels are shortened.',
    entries: [
      { term: '€/MWh', meaning: 'Day-ahead market price per megawatt-hour. The German power market quotes prices this way.', example: '€111/MWh = €0.111/kWh' },
      { term: '€/kWh', meaning: 'Price per kilowatt-hour. Used for grid fees, levies and the export price.' },
      { term: '€/kW·yr', meaning: 'Peak charge: euros per kW of the year’s highest 15-minute grid draw, billed for the whole year.', example: '26,180 kW × €85 = €2,225,300 a year' },
      { term: '€140k · €2.2M', meaning: 'Short chart labels: k = thousand, M = million.' },
      { term: 'Negative price', meaning: 'The market pays consumers to take power, often on sunny, windy days. The planner moves flexible work into these hours.' },
    ],
  },
  {
    title: 'Weather and emissions',
    description: 'Site weather drives the solar and wind forecasts.',
    entries: [
      { term: 'W/m² (watts per square metre)', meaning: 'Sunlight on the tilted solar panels. Bright midday sun is about 800–1,000 W/m².' },
      { term: 'm/s (metres per second)', meaning: 'Wind speed at the turbine’s hub height. Most turbines start at about 3 m/s and reach full output at 12–14 m/s.', example: '10 m/s ≈ 36 km/h' },
      { term: '°C · cloud %', meaning: 'Air temperature (hot panels produce a little less) and the share of the sky covered by cloud.' },
      { term: 'kg CO₂/kWh', meaning: 'Emissions per kWh taken from the German grid. Used to estimate CO₂ avoided by using on-site power.' },
      { term: 't CO₂', meaning: 'Tonnes of carbon dioxide; 1 t = 1,000 kg.' },
    ],
  },
  {
    title: 'Time',
    description: 'Everything is shown in German time, whatever your computer’s time zone.',
    entries: [
      { term: 'CET · CEST', meaning: 'Central European Time (winter, UTC+1) and Central European Summer Time (UTC+2). The clock in the top bar shows which applies now.' },
      { term: '24h · 12h', meaning: 'Switch in the top bar between 24-hour (14:00) and 12-hour (2:00 pm) times.' },
      { term: 'Horizon', meaning: 'The 7 days (168 hours) each plan covers, starting at the next midnight.' },
      { term: 'h', meaning: 'Hours, e.g. run hours scheduled for a machine (126/126 h = all required hours planned).' },
      { term: '15-minute interval', meaning: 'Meter readings come every 15 minutes; the peak charge uses the highest of these.' },
    ],
  },
  {
    title: 'Plan terms',
    description: 'Words used on the Overview, Forecast and in the daily email.',
    entries: [
      { term: 'Day-ahead price', meaning: 'Hourly price set the day before on the power exchange (EPEX, DE-LU zone). Tomorrow’s prices come out around 13:00 German time.' },
      { term: 'Real', meaning: 'A published market price.', symbol: <Stripe estimate={false} /> },
      { term: 'Estimate', meaning: 'Prices not published yet, predicted from the weather and past prices. Re-planned once real prices arrive.', symbol: <Stripe estimate /> },
      { term: 'Run-as-needed', meaning: 'The comparison case: every machine runs as early as it is allowed to, with no planning. Savings are measured against it.' },
      { term: 'Savings', meaning: 'Run-as-needed cost minus the GridShift plan’s cost for the same week, same work.' },
      { term: 'Base load', meaning: 'Power the plant always uses: always-on machines, lighting, offices. Learned from past meter data.' },
      { term: 'Flexible load', meaning: 'Machines whose run times GridShift may move (daily quota and deadline jobs).' },
      { term: 'Grid draw (import)', meaning: 'Power taken from the grid in an hour.' },
      { term: 'Export', meaning: 'Surplus on-site power sold back to the grid.' },
      { term: 'Peak record', meaning: 'This year’s highest 15-minute grid draw so far. Going above it raises the peak charge for the whole year.' },
      { term: 'Renewable share', meaning: 'Share of the plant’s energy that came from its own solar and wind.' },
      { term: 'Curtailed', meaning: 'On-site power that could not be used, stored or exported.' },
      { term: 'Unmet demand', meaning: 'Load the grid connection and on-site supply could not cover. Shown as an alert.' },
    ],
  },
  {
    title: 'Machine types',
    description: 'How each machine may be scheduled.',
    entries: [
      { term: 'Always on', meaning: 'Runs 24/7. Part of the base load; never moved.', symbol: <Badge>Always on</Badge>, symbolOnly: true },
      { term: 'Daily quota', meaning: 'Must run a set number of hours every day; GridShift picks which hours.', symbol: <Badge tone="info">Daily quota</Badge>, symbolOnly: true },
      { term: 'Deadline job', meaning: 'Needs a total number of hours before a due time; GridShift picks the days and hours.', symbol: <Badge tone="warning">Deadline job</Badge>, symbolOnly: true },
      { term: 'Shortest run', meaning: 'Once started, the machine runs at least this many hours in a row.' },
    ],
  },
  {
    title: 'Chart symbols',
    description: 'Colours and lines used on the Forecast and Schedule charts.',
    entries: [
      { term: 'Published price', meaning: 'Solid orange line.', symbol: <Line color="var(--series-price)" /> },
      { term: 'Estimated price', meaning: 'Dashed orange line.', symbol: <Line color="var(--series-price)" dashed /> },
      { term: 'Already past', meaning: 'Grey line for hours before now.', symbol: <Line color="var(--series-grid)" /> },
      { term: 'Now', meaning: 'Vertical line at the current time.', symbol: <Line color="var(--fg)" width={1.5} /> },
      { term: 'Next prices published', meaning: 'Dashed blue line where the next day’s prices are expected.', symbol: <Line color="var(--info)" dashed width={1.5} /> },
      { term: 'Peak record', meaning: 'Red line: this year’s highest grid draw.', symbol: <Line color="var(--danger)" /> },
      { term: 'Solar', meaning: 'Yellow area: expected solar output.', symbol: <Swatch color="var(--series-solar)" /> },
      { term: 'Wind', meaning: 'Blue area: expected wind output.', symbol: <Swatch color="var(--series-wind)" /> },
      { term: 'Planned factory load', meaning: 'Dark line: base load plus scheduled machines.', symbol: <Line color="var(--series-demand)" /> },
      { term: 'Battery charge level', meaning: 'Purple area: state of charge.', symbol: <Swatch color="var(--series-battery)" /> },
      { term: 'Charging · discharging', meaning: 'Green bars charge the battery; orange bars draw from it.', symbol: <span className="flex gap-1"><Swatch color="var(--positive)" /><Swatch color="var(--series-price)" /></span> },
      { term: 'GridShift plan · run-as-needed', meaning: 'Blue bars are the plan; grey bars are the comparison case.', symbol: <span className="flex gap-1"><Swatch color="var(--brand)" /><Swatch color="var(--series-baseline)" /></span> },
    ],
  },
  {
    title: 'Labels and status',
    description: 'Small labels that say where data came from.',
    entries: [
      { term: 'live', meaning: 'Fetched fresh for this plan.', symbol: <Badge tone="positive">live</Badge>, symbolOnly: true },
      { term: 'cached', meaning: 'The weather service was down, so the last saved forecast was used.', symbol: <Badge tone="warning">cached</Badge>, symbolOnly: true },
      { term: 'estimated', meaning: 'The price services were down, so every hour uses the estimate.', symbol: <Badge tone="warning">estimated</Badge>, symbolOnly: true },
      { term: 'Sample data', meaning: 'The built-in Holcim example: illustrative figures, not a real plant. Switch it off in the sidebar to use your own site.', symbol: <Badge tone="info">Sample data</Badge>, symbolOnly: true },
      { term: 'success · failure', meaning: 'Outcome of an action in the audit log.', symbol: <span className="flex gap-1"><Badge tone="positive">success</Badge><Badge tone="danger">failure</Badge></span>, symbolOnly: true },
    ],
  },
]

function matches(entry: Entry, query: string): boolean {
  return `${entry.term} ${entry.meaning} ${entry.example ?? ''}`.toLowerCase().includes(query)
}

/** Reference for the units, terms and symbols used across GridShift. */
export function GuidePage() {
  const [query, setQuery] = useState('')
  const q = query.trim().toLowerCase()
  const sections = useMemo(() => SECTIONS.map((s) => ({ ...s, entries: q ? s.entries.filter((e) => matches(e, q)) : s.entries })).filter((s) => s.entries.length), [q])

  return (
    <PageLayout title="Units & terms" subtitle="What every unit, label and chart symbol in GridShift means" planActions={false}>
      <div className="relative mb-6 max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search, e.g. kWh, peak, estimate" aria-label="Search units and terms" className="pl-9" />
      </div>
      {sections.length === 0 ? (
        <p className="text-sm text-muted">Nothing matches “{query}”.</p>
      ) : (
        <div className="grid gap-6 xl:grid-cols-2">
          {sections.map((section) => (
            <Card key={section.title} className="h-fit">
              <CardHeader title={section.title} description={section.description} />
              <CardBody>
                <dl className="divide-y divide-border">
                  {section.entries.map((entry) => (
                    <div key={entry.term} className="grid gap-1 py-3 first:pt-0 last:pb-0 sm:grid-cols-[minmax(0,13rem)_1fr] sm:gap-4">
                      <dt className="flex items-center gap-2 font-medium text-fg">
                        {entry.symbol}
                        {entry.symbolOnly ? <span className="sr-only">{entry.term}</span> : <span>{entry.term}</span>}
                      </dt>
                      <dd className="text-sm text-muted">
                        {entry.meaning}
                        {entry.example && <span className="tabular mt-0.5 block text-fg">{entry.example}</span>}
                      </dd>
                    </div>
                  ))}
                </dl>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </PageLayout>
  )
}
