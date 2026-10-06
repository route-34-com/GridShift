import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { num } from '@/lib/format'
import type { ChartHour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { activeRow, axisProps, hourTitle, isPast, nowLine, PAST_COLOR, toRows, TooltipBox, xAxisProps, type TooltipArgs } from './common'

interface PriceChartProps {
  hours: ChartHour[]
  /** Current time in ms; hours already gone turn grey and a "Now" line marks it. */
  now?: number
  nowLabel?: string
  /** When the next day's prices are published, marked with a dashed line. */
  release?: { t: number; label: string } | null
}

export function PriceChart({ hours, now, nowLabel = 'Now', release }: PriceChartProps) {
  const at = now ?? -Infinity
  const firstFuture = hours.findIndex((h) => !isPast(new Date(h.ts).getTime(), at))
  const rows = toRows(hours, (h, i) => {
    const t = new Date(h.ts).getTime()
    const past = isPast(t, at)
    const next = hours[i + 1]
    const boundary = h.price_source === 'actual' && next?.price_source === 'estimate'
    return {
      past: past || i === firstFuture ? h.price : null,
      actual: !past && h.price_source === 'actual' ? h.price : null,
      estimate: !past && (h.price_source === 'estimate' || boundary) ? h.price : null,
      source: h.price_source === 'actual' ? 1 : 0,
      gone: past ? 1 : 0,
    }
  })
  const hasNegative = hours.some((h) => (h.price ?? 0) < 0)
  const marker = now != null ? nowLine(rows, now, nowLabel) : null
  const releaseOnChart = release && rows.length > 0 && release.t >= rows[0].t && release.t <= rows[rows.length - 1].t ? release : null

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis {...axisProps} width={44} tickFormatter={(v: number) => num(v)} unit="" />
        {hasNegative && <ReferenceLine y={0} stroke="var(--muted)" strokeDasharray="2 2" />}
        {marker && <ReferenceLine {...marker} />}
        {releaseOnChart && (
          <ReferenceLine
            x={releaseOnChart.t}
            stroke="var(--info)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            label={{ value: releaseOnChart.label, position: 'insideBottomLeft', fontSize: 11, fontWeight: 600, fill: 'var(--info)', offset: 6 }}
          />
        )}
        <Tooltip
          content={(args: TooltipArgs) => {
            const row = activeRow(args)
            if (!row) return null
            const value = (row.actual ?? row.estimate ?? row.past) as number | null
            return (
              <TooltipBox
                title={hourTitle(row.t)}
                lines={[{ label: 'Price', color: row.gone ? PAST_COLOR : SERIES.price, value: value == null ? '–' : `€${num(value, 1)}/MWh` }]}
                footer={row.gone ? 'Already past' : row.source ? 'Published day-ahead price' : 'Estimated from weather forecast'}
              />
            )
          }}
        />
        <Line dataKey="past" stroke={PAST_COLOR} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
        {/* A wide faint copy under the line gives it a glow without a costly SVG filter. */}
        <Line dataKey="actual" stroke={SERIES.price} strokeWidth={7} strokeOpacity={0.18} dot={false} activeDot={false} isAnimationActive={false} connectNulls={false} legendType="none" tooltipType="none" />
        <Line dataKey="actual" stroke={SERIES.price} strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
        <Line
          dataKey="estimate"
          stroke={SERIES.price}
          strokeWidth={2}
          strokeDasharray="5 4"
          strokeOpacity={0.75}
          dot={false}
          isAnimationActive={false}
          connectNulls={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
