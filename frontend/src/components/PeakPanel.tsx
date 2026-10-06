import { Mountain } from 'lucide-react'
import type { ReactNode } from 'react'
import { CountUp } from '@/components/CountUp'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { dateTime, eur, kw, num } from '@/lib/format'
import type { PeakRecord } from '@/lib/types'

function Figure({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-surface-2 p-3.5">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className="tabular mt-1 truncate font-mono text-xl font-semibold text-fg">{typeof value === 'string' ? <CountUp text={value} /> : value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  )
}

function peakSource(peak: PeakRecord): string {
  if (peak.source === 'meter') return peak.at ? `Set ${dateTime(peak.at)} · from meter data` : 'From meter data'
  return peak.meter_kw !== null ? `From site settings (meter shows ${kw(peak.meter_kw)})` : 'From site settings · upload meter data to find it automatically'
}

interface PeakPanelProps {
  peak: PeakRecord
  planHighestKw?: number
  action?: ReactNode
  children?: ReactNode
}

export function PeakPanel({ peak, planHighestKw, action, children }: PeakPanelProps) {
  const rate = peak.charge_eur_per_kw_year
  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <Mountain className="h-4 w-4 text-brand" aria-hidden /> {peak.year} peak charge
          </span>
        }
        description="The grid operator bills this year's highest 15-minute grid draw at a yearly price per kW."
        action={action}
      />
      <CardBody className="space-y-3 pt-3">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Figure label="Highest draw this year" value={kw(peak.record_kw)} hint={peakSource(peak)} />
          <Figure label="Peak charge per month" value={eur(peak.monthly_eur)} hint={`${num(peak.record_kw)} kW × €${num(rate)} ÷ 12`} />
          <Figure label="Peak charge per year" value={eur(peak.annual_eur)} hint={`€${num(rate)} per kW per year`} />
          {planHighestKw !== undefined ? (
            <Figure
              label="This week's plan"
              value={kw(planHighestKw)}
              hint={planHighestKw <= peak.record_kw + 0.5 ? `${kw(peak.record_kw - planHighestKw)} below the record` : `${kw(planHighestKw - peak.record_kw)} above the record`}
            />
          ) : (
            <Figure label="Each extra kW" value={eur(rate)} hint="added to this year's charge" />
          )}
        </div>
        {children}
      </CardBody>
    </Card>
  )
}
