import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { eur, eurShort } from '@/lib/format'
import type { Day } from '@/lib/types'
import { SERIES } from '@/lib/utils'
import { axisProps, TooltipBox } from './common'

interface DayRow {
  label: string
  plan: number
  baseline: number
  estimated: boolean
}

interface DayTooltipArgs {
  active?: boolean
  payload?: readonly { payload?: DayRow }[]
}

export function DailyCostChart({ days }: { days: Day[] }) {
  const rows: DayRow[] = days.map((d) => ({
    label: d.label.slice(0, 3),
    plan: d.cost_eur,
    baseline: d.baseline_cost_eur,
    estimated: d.price_estimated,
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barGap={4} barCategoryGap="22%">
        <CartesianGrid vertical={false} />
        <XAxis dataKey="label" {...axisProps} />
        <YAxis {...axisProps} width={56} tickFormatter={(v: number) => eurShort(v)} />
        <Tooltip
          cursor={{ fill: 'var(--surface-2)' }}
          content={(args: DayTooltipArgs) => {
            const row = args.active && args.payload?.length ? (args.payload[0].payload ?? null) : null
            if (!row) return null
            return (
              <TooltipBox
                title={days.find((d) => d.label.startsWith(row.label))?.label ?? row.label}
                lines={[
                  { label: 'GridShift plan', color: SERIES.brand, value: eur(row.plan) },
                  { label: 'Run-as-needed', color: SERIES.baseline, value: eur(row.baseline) },
                ]}
                footer={row.estimated ? 'Uses estimated prices' : 'Uses published prices'}
              />
            )
          }}
        />
        <Bar dataKey="baseline" fill={SERIES.baseline} radius={[4, 4, 0, 0]} isAnimationActive={false} />
        <Bar dataKey="plan" fill={SERIES.brand} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
