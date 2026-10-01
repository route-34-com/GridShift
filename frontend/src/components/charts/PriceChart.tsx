import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { num } from '@/lib/format'
import type { Hour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { activeRow, axisProps, hourTitle, toRows, TooltipBox, xAxisProps, type TooltipArgs } from './common'

export function PriceChart({ hours }: { hours: Hour[] }) {
  const rows = toRows(hours, (h, i) => {
    const next = hours[i + 1]
    const boundary = h.price_source === 'actual' && next?.price_source === 'estimate'
    return {
      actual: h.price_source === 'actual' ? h.price : null,
      estimate: h.price_source === 'estimate' || boundary ? h.price : null,
      source: h.price_source === 'actual' ? 1 : 0,
    }
  })
  const hasNegative = hours.some((h) => h.price < 0)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis {...axisProps} width={44} tickFormatter={(v: number) => num(v)} unit="" />
        {hasNegative && <ReferenceLine y={0} stroke="var(--muted)" strokeDasharray="2 2" />}
        <Tooltip
          content={(args: TooltipArgs) => {
            const row = activeRow(args)
            if (!row) return null
            const value = (row.actual ?? row.estimate) as number
            return (
              <TooltipBox
                title={hourTitle(row.t)}
                lines={[{ label: 'Price', color: SERIES.price, value: `€${num(value, 1)}/MWh` }]}
                footer={row.source ? 'Published day-ahead price' : 'Estimated from weather forecast'}
              />
            )
          }}
        />
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
