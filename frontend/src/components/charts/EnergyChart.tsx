import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { power } from '@/lib/format'
import type { Hour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { activeRow, axisProps, hourTitle, toRows, TooltipBox, xAxisProps, type TooltipArgs } from './common'

export function EnergyChart({ hours }: { hours: Hour[] }) {
  const rows = toRows(hours, (h) => ({
    solar: h.solar,
    wind: h.wind,
    load: h.demand + h.flexible,
    base: h.demand,
    grid: h.grid_import,
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis {...axisProps} width={64} tickFormatter={(v: number) => power(v)} />
        <Tooltip
          content={(args: TooltipArgs) => {
            const row = activeRow(args)
            if (!row) return null
            return (
              <TooltipBox
                title={hourTitle(row.t)}
                lines={[
                  { label: 'Solar', color: SERIES.solar, value: power(row.solar as number) },
                  { label: 'Wind', color: SERIES.wind, value: power(row.wind as number) },
                  { label: 'Factory load', color: SERIES.demand, value: power(row.load as number) },
                  { label: 'Base load', color: SERIES.baseline, value: power(row.base as number) },
                  { label: 'Grid import', color: SERIES.grid, value: power(row.grid as number) },
                ]}
              />
            )
          }}
        />
        <Area dataKey="wind" stackId="re" stroke={SERIES.wind} fill={SERIES.wind} fillOpacity={0.35} strokeWidth={1} isAnimationActive={false} />
        <Area dataKey="solar" stackId="re" stroke={SERIES.solar} fill={SERIES.solar} fillOpacity={0.45} strokeWidth={1} isAnimationActive={false} />
        <Line dataKey="base" stroke={SERIES.baseline} strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
        <Line dataKey="load" stroke={SERIES.demand} strokeWidth={2} dot={false} type="stepAfter" isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
