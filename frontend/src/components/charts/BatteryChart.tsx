import { Area, Bar, CartesianGrid, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { energy, pct, power } from '@/lib/format'
import type { Hour } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { activeRow, axisProps, hourTitle, toRows, TooltipBox, xAxisProps, type TooltipArgs } from './common'

export function BatteryChart({ hours, capacity }: { hours: Hour[]; capacity: number }) {
  const rows = toRows(hours, (h) => ({
    soc: capacity > 0 ? h.soc / capacity : 0,
    socKwh: h.soc,
    flow: h.charge - h.discharge,
  }))
  const maxFlow = Math.max(1, ...hours.map((h) => Math.max(h.charge, h.discharge)))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="battery-soc" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={SERIES.battery} stopOpacity={0.4} />
            <stop offset="100%" stopColor={SERIES.battery} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} />
        <XAxis {...xAxisProps(hours)} />
        <YAxis yAxisId="soc" {...axisProps} width={44} domain={[0, 1]} tickFormatter={(v: number) => pct(v)} />
        <YAxis yAxisId="flow" orientation="right" {...axisProps} width={64} domain={[-maxFlow, maxFlow]} tickFormatter={(v: number) => power(v)} />
        <Tooltip
          content={(args: TooltipArgs) => {
            const row = activeRow(args)
            if (!row) return null
            const flow = row.flow as number
            return (
              <TooltipBox
                title={hourTitle(row.t)}
                lines={[
                  { label: 'State of charge', color: SERIES.battery, value: `${pct(row.soc as number)} · ${energy(row.socKwh as number)}` },
                  {
                    label: flow >= 0 ? 'Charging' : 'Discharging',
                    color: flow >= 0 ? 'var(--positive)' : SERIES.price,
                    value: power(Math.abs(flow)),
                  },
                ]}
              />
            )
          }}
        />
        <Bar
          yAxisId="flow"
          dataKey="flow"
          isAnimationActive={false}
          shape={(props: { x?: number; y?: number; width?: number; height?: number; value?: number | [number, number] }) => {
            const { x = 0, y = 0, width = 0, height = 0 } = props
            const value = Array.isArray(props.value) ? props.value[1] - props.value[0] : (props.value ?? 0)
            const top = height < 0 ? y + height : y
            return <rect x={x} y={top} width={Math.max(1, width)} height={Math.abs(height)} fill={value >= 0 ? 'var(--positive)' : SERIES.price} opacity={0.55} />
          }}
        />
        <Area yAxisId="soc" dataKey="soc" stroke={SERIES.battery} fill="url(#battery-soc)" strokeWidth={2} type="monotone" isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
