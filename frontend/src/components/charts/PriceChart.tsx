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
}

export function PriceChart({ hours, now, nowLabel = 'Now' }: PriceChartProps) {
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

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis {...axisProps} width={44} tickFormatter={(v: number) => num(v)} unit="" />
        {hasNegative && <ReferenceLine y={0} stroke="var(--muted)" strokeDasharray="2 2" />}
        {marker && <ReferenceLine {...marker} />}
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
