import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { num, power } from '@/lib/format'
import { SERIES } from '@/lib/utils'
import { turbineMarks } from '@/lib/weather'
import { axisProps, TooltipBox } from './common'

interface PowerCurveChartProps {
  curve: [number, number][]
  ratedKw: number
  height?: number
}

interface CurveRow {
  speed: number
  kw: number
}

interface CurveTooltipArgs {
  active?: boolean
  payload?: readonly { payload?: CurveRow }[]
}

/** Turbine output against hub-height wind speed, drawn with straight segments as the planner interpolates them. */
export function PowerCurveChart({ curve, ratedKw, height = 240 }: PowerCurveChartProps) {
  const rows: CurveRow[] = curve.map(([speed, kw]) => ({ speed, kw: ratedKw > 0 ? Math.min(kw, ratedKw) : kw }))
  const marks = turbineMarks(curve, ratedKw)
  const fastest = Math.max(...curve.map(([s]) => s), 0)
  const right = Math.min(fastest, Math.max(30, (marks?.stopsAt ?? 0) + 5))
  const top = Math.max(ratedKw, ...rows.map((r) => r.kw), 1)
  const speedLine = (speed: number | null | undefined, label: string) =>
    speed != null && (
      <ReferenceLine
        x={speed}
        stroke="var(--muted)"
        strokeDasharray="2 3"
        ifOverflow="discard"
        label={{ value: label, position: 'top', fontSize: 11, fill: 'var(--muted)' }}
      />
    )

  return (
    <div style={{ height }} role="img" aria-label={`Power curve: ${rows.length} points${marks ? `, starts at ${marks.startsAt} m/s, full power at ${marks.fullAt ?? '–'} m/s` : ''}`}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 22, right: 24, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            {...axisProps}
            dataKey="speed"
            type="number"
            domain={[0, right]}
            allowDataOverflow
            tickCount={7}
            tickFormatter={(v: number) => `${v}`}
            label={{ value: 'Wind speed at hub (m/s)', position: 'insideBottomRight', offset: -2, fontSize: 11, fill: 'var(--muted)' }}
            height={36}
          />
          <YAxis {...axisProps} width={64} domain={[0, Math.ceil(top * 1.08)]} ticks={ratedKw > 0 ? [0, 1, 2, 3].map((k) => Math.round((ratedKw * k) / 3)) : undefined} tickFormatter={(v: number) => (top >= 2000 ? `${num(v / 1000, 1)} MW` : `${num(v)} kW`)} />
          {ratedKw > 0 && (
            <ReferenceLine y={ratedKw} stroke="var(--muted)" strokeDasharray="2 3" />
          )}
          {speedLine(marks?.startsAt, 'Starts')}
          {marks?.fullAt !== marks?.startsAt && speedLine(marks?.fullAt, 'Full power')}
          {speedLine(marks?.stopsAt, 'Storm stop')}
          <Tooltip
            cursor={{ stroke: 'var(--border)' }}
            content={(args: CurveTooltipArgs) => {
              const row = args.active ? args.payload?.[0]?.payload : undefined
              if (!row) return null
              return (
                <TooltipBox
                  title={`${num(row.speed, 1)} m/s · ${num(row.speed * 3.6)} km/h`}
                  lines={[{ label: 'Turbine output', color: SERIES.wind, value: power(row.kw) }]}
                  footer={ratedKw > 0 ? `${num((row.kw / ratedKw) * 100)}% of rated power` : undefined}
                />
              )
            }}
          />
          <Line
            dataKey="kw"
            type="linear"
            stroke={SERIES.wind}
            strokeWidth={2}
            dot={{ r: 4, fill: SERIES.wind, stroke: 'var(--surface-solid)', strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: 'var(--surface-solid)', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
