import { useState, type FormEvent, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, FormError, Input } from '@/components/ui/field'
import { EMPTY_SITE } from '@/lib/site'
import type { SiteConfig } from '@/lib/types'

type Values = Record<string, string>

const PERCENT = new Set(['solar.performance_ratio', 'battery.efficiency', 'battery.min_soc', 'battery.initial_soc'])

const SECTIONS: { title: string; note?: string; fields: [string, string, string?][] }[] = [
  { title: 'Plant', fields: [['name', 'Site name'], ['latitude', 'Latitude (°N)'], ['longitude', 'Longitude (°E)']] },
  {
    title: 'Grid and prices',
    note: 'From the grid connection contract and the electricity bill.',
    fields: [
      ['grid.max_import_kw', 'Grid connection limit (kW)'],
      ['grid.max_export_kw', 'Export limit (kW)'],
      ['grid.fee_eur_per_kwh', 'Fees and levies (€/kWh)', 'Grid fees, levies and taxes on top of the market price'],
      ['grid.export_price_eur_per_kwh', 'Export price (€/kWh)'],
      ['grid.peak_charge_eur_per_kw_year', 'Peak charge (€ per kW per year)', 'Leistungspreis; 0 turns peak protection off'],
      ['grid.peak_so_far_kw', 'Highest kW this year (from the bill)', 'Meter data uploaded on this page wins if it is higher'],
    ],
  },
  {
    title: 'Solar',
    note: 'Leave peak power at 0 if there is no solar.',
    fields: [
      ['solar.kwp', 'Peak power (kWp)'],
      ['solar.tilt', 'Tilt (°)'],
      ['solar.azimuth', 'Direction (°, 0 = south, -90 = east)'],
      ['solar.performance_ratio', 'Performance ratio (%)'],
    ],
  },
  {
    title: 'Battery',
    note: 'Leave capacity at 0 if there is no battery.',
    fields: [
      ['battery.capacity_kwh', 'Capacity (kWh)'],
      ['battery.max_charge_kw', 'Max charging (kW)'],
      ['battery.max_discharge_kw', 'Max discharging (kW)'],
      ['battery.efficiency', 'Efficiency each way (%)'],
      ['battery.min_soc', 'Lowest charge level (%)'],
      ['battery.initial_soc', 'Charge level at plan start (%)'],
    ],
  },
  { title: 'Wind turbine', note: 'Leave rated power at 0 if there is no turbine.', fields: [['wind.rated_kw', 'Rated power (kW)'], ['wind.hub_height_m', 'Hub height (m)']] },
  { title: 'Reporting', fields: [['co2_kg_per_kwh', 'Grid CO₂ (kg per kWh)'], ['email_recipients', 'Daily plan email to', 'Separate addresses with commas']] },
]

function read(site: SiteConfig, path: string): unknown {
  return path.split('.').reduce<unknown>((obj, key) => (obj as Record<string, unknown>)[key], site)
}

function toValues(site: SiteConfig): Values {
  const values: Values = { curve: site.wind.power_curve.map(([speed, kw]) => `${speed} ${kw}`).join('\n') }
  for (const section of SECTIONS) {
    for (const [path] of section.fields) {
      const value = read(site, path)
      values[path] = Array.isArray(value) ? value.join(', ') : PERCENT.has(path) ? String(Math.round(Number(value) * 1000) / 10) : String(value)
    }
  }
  return values
}

function toSite(values: Values): SiteConfig | string {
  const site = structuredClone(EMPTY_SITE)
  for (const section of SECTIONS) {
    for (const [path, label] of section.fields) {
      const raw = values[path]?.trim() ?? ''
      const keys = path.split('.')
      const parent = keys.slice(0, -1).reduce<Record<string, unknown>>((obj, key) => obj[key] as Record<string, unknown>, site as unknown as Record<string, unknown>)
      const key = keys[keys.length - 1]
      if (path === 'name') {
        if (!raw) return 'Give the site a name.'
        parent[key] = raw
      } else if (path === 'email_recipients') {
        parent[key] = raw ? raw.split(/[\s,;]+/).filter(Boolean) : []
      } else {
        const number = Number(raw.replace(',', '.'))
        if (raw === '' || !Number.isFinite(number)) return `${label} needs a number.`
        parent[key] = PERCENT.has(path) ? number / 100 : number
      }
    }
  }
  const curve = (values.curve ?? '')
    .split('\n')
    .map((line) => line.trim().split(/[\s;,]+/).map(Number))
    .filter((pair) => pair.length === 2 && pair.every(Number.isFinite)) as [number, number][]
  if (site.wind.rated_kw > 0 && curve.length < 2) return 'A wind turbine needs a power curve with at least two "speed kW" lines.'
  site.wind.power_curve = curve.length >= 2 ? curve : EMPTY_SITE.wind.power_curve
  return site
}

interface SiteDialogProps {
  open: boolean
  site: SiteConfig | null
  onClose: () => void
  onSave: (site: SiteConfig) => Promise<string | null>
}

function Section({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-semibold text-fg">{title}</legend>
      {note && <p className="-mt-1 text-xs text-muted">{note}</p>}
      <div className="grid gap-3 sm:grid-cols-2">{children}</div>
    </fieldset>
  )
}

export function SiteDialog({ open, site, onClose, onSave }: SiteDialogProps) {
  const [values, setValues] = useState<Values>(() => toValues(site ?? EMPTY_SITE))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const built = toSite(values)
    if (typeof built === 'string') return setError(built)
    setBusy(true)
    const problem = await onSave(built)
    setBusy(false)
    if (problem) setError(problem)
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()} title={site ? 'Edit site settings' : 'Add site details'} description="Used for the weather forecast, on-site generation, the battery and grid costs." wide>
      <form onSubmit={(e) => void submit(e)} className="space-y-6">
        {SECTIONS.map((section) => (
          <Section key={section.title} title={section.title} note={section.note}>
            {section.fields.map(([path, label, hint]) => (
              <Field key={path} label={label} hint={hint}>
                {(id) => (
                  <Input
                    id={id}
                    value={values[path] ?? ''}
                    inputMode={path === 'name' || path === 'email_recipients' ? undefined : 'decimal'}
                    onChange={(e) => setValues((v) => ({ ...v, [path]: e.target.value }))}
                  />
                )}
              </Field>
            ))}
            {section.title === 'Wind turbine' && (
              <div className="sm:col-span-2">
                <Field label="Power curve" hint='One "wind speed in m/s, power in kW" pair per line, from the turbine datasheet.'>
                  {(id) => (
                    <textarea
                      id={id}
                      rows={5}
                      value={values.curve}
                      onChange={(e) => setValues((v) => ({ ...v, curve: e.target.value }))}
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2 font-mono text-sm text-fg focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/30 focus-visible:outline-none"
                    />
                  )}
                </Field>
              </div>
            )}
          </Section>
        ))}
        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-border pt-4">
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save site'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
