import { Area, CartesianGrid, ComposedChart, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { num, power } from '@/lib/format'
import type { ChartHour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { CLOUD_COLOR, type TurbineMarks } from '@/lib/weather'
import { activeRow, axisProps, hourTitle, isPast, nowLine, PAST_COLOR, splitAtNow, toRows, TooltipBox, xAxisProps, type Row, type TooltipArgs } from './common'

const value = (v: number | null | undefined, unit: string, digits = 0) => (v == null ? '–' : `${num(v, digits)} ${unit}`)

interface NowProps {
  /** Current time in ms; hours already gone turn grey and a "Now" line marks it. */
  now?: number
  nowLabel?: string
}

export function SunlightChart({ hours, now, nowLabel = 'Now' }: { hours: ChartHour[] } & NowProps) {
  const at = now ?? -Infinity
  const base = toRows(hours, (h) => ({
    sun: h.sunlight_w_m2 ?? null,
    cloud: h.cloud_cover_pct ?? null,
    temp: h.temperature_c ?? null,
    solar: h.solar ?? null,
  }))
  const rows = splitAtNow(base, 'sun', at).map((r): Row => ({ ...r, gone: isPast(r.t, at) ? 1 : 0 }))
  const hasClouds = rows.some((r) => r.cloud != null)
  const marker = now != null ? nowLine(rows, now, nowLabel) : null

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="sunlight-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={SERIES.solar} stopOpacity={0.55} />
            <stop offset="100%" stopColor={SERIES.solar} stopOpacity={0.04} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis yAxisId="sun" {...axisProps} width={44} tickFormatter={(v: number) => num(v)} />
        <YAxis yAxisId="cloud" orientation="right" {...axisProps} width={40} domain={[0, 100]} ticks={[0, 50, 100]} tickFormatter={(v: number) => `${v}%`} hide={!hasClouds} />
        {marker && <ReferenceLine yAxisId="sun" {...marker} />}
        <Tooltip
          content={(args: TooltipArgs) => {
            const row = activeRow(args)
            if (!row) return null
            return (
              <TooltipBox
                title={hourTitle(row.t)}
                lines={[
                  { label: 'Sunlight on panels', color: row.gone ? PAST_COLOR : SERIES.solar, value: value(row.sun, 'W/m²') },
                  { label: 'Cloud cover', color: CLOUD_COLOR, value: value(row.cloud, '%') },
                  { label: 'Temperature', color: 'var(--muted)', value: value(row.temp, '°C', 1) },
                ]}
                footer={row.gone ? 'Already past' : row.solar == null ? 'Before the plan starts' : `Solar output ${power(row.solar)}`}
              />
            )
          }}
        />
        <Area yAxisId="sun" dataKey="sunPast" stroke={PAST_COLOR} fill={PAST_COLOR} fillOpacity={0.15} strokeWidth={1.5} isAnimationActive={false} connectNulls={false} />
        <Area yAxisId="sun" dataKey="sunNext" stroke={SERIES.solar} fill="url(#sunlight-fill)" strokeWidth={2} isAnimationActive={false} connectNulls={false} />
        {hasClouds && <Line yAxisId="cloud" dataKey="cloud" stroke={CLOUD_COLOR} strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />}
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function WindChart({ hours, marks, now, nowLabel = 'Now' }: { hours: ChartHour[]; marks: TurbineMarks | null } & NowProps) {
  const at = now ?? -Infinity
  const rows = splitAtNow(
    toRows(hours, (h) => ({ speed: h.wind_ms ?? null, output: h.wind ?? null })),
    'speed',
    at,
  ).map((r): Row => ({ ...r, gone: isPast(r.t, at) ? 1 : 0 }))
  const marker = now != null ? nowLine(rows, now, nowLabel) : null
  const fastest = Math.max(0, ...rows.map((r) => r.speed ?? 0))
  const top = Math.ceil(Math.max(fastest, marks?.fullAt ?? 0) + 1)
  const line = (speed: number | null | undefined, label: string) =>
    speed != null && (
      <ReferenceLine
        y={speed}
        stroke="var(--muted)"
        strokeDasharray="2 3"
        ifOverflow="discard"
        label={{ value: label, position: 'insideTopLeft', fontSize: 11, fill: 'var(--muted)' }}
      />
    )

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis {...axisProps} width={44} domain={[0, top]} tickFormatter={(v: number) => `${v}`} />
        {marker && <ReferenceLine {...marker} />}
        {line(marks?.startsAt, 'Turbine starts')}
        {line(marks?.fullAt, 'Full power')}
        {line(marks?.stopsAt, 'Shuts off (storm)')}
        <Tooltip
          content={(args: TooltipArgs) => {
            const row = activeRow(args)
            if (!row) return null
            const speed = row.speed as number | null
            return (
              <TooltipBox
                title={hourTitle(row.t)}
                lines={[{ label: 'Wind at hub', color: row.gone ? PAST_COLOR : SERIES.wind, value: speed == null ? '–' : `${num(speed, 1)} m/s · ${num(speed * 3.6)} km/h` }]}
                footer={row.gone ? 'Already past' : marks && row.output != null ? `Turbine output ${power(row.output)}` : undefined}
              />
            )
          }}
        />
        <Line dataKey="speedPast" stroke={PAST_COLOR} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
        <Line dataKey="speedNext" stroke={SERIES.wind} strokeWidth={7} strokeOpacity={0.16} dot={false} activeDot={false} isAnimationActive={false} connectNulls={false} legendType="none" tooltipType="none" />
        <Line dataKey="speedNext" stroke={SERIES.wind} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
