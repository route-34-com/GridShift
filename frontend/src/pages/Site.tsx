import { BatteryCharging, Cable, Check, CircleAlert, Copy, FlaskConical, Pencil, Plus, Sun, Trash2, Upload, Wind } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { PageLayout } from '@/components/PageLayout'
import { PeakPanel } from '@/components/PeakPanel'
import { MachineDialog } from '@/components/setup/MachineDialog'
import { SiteDialog } from '@/components/setup/SiteDialog'
import { ErrorView, LoadingView } from '@/components/StateViews'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { useAuth } from '@/hooks/AuthContext'
import { useToast } from '@/hooks/Toasts'
import { useAsync } from '@/hooks/useAsync'
import { useRun } from '@/hooks/RunContext'
import { api } from '@/lib/api'
import { dateTime, dayLabel, energy, eur, kw, num, pct, power } from '@/lib/format'
import type { MachineConfig, SiteConfig, SiteSetup } from '@/lib/types'
import { cn } from '@/lib/utils'

function Spec({ icon: Icon, title, rows }: { icon: LucideIcon; title: string; rows: [string, ReactNode][] }) {
  return (
    <Card>
      <CardBody>
        <div className="mb-4 flex items-center gap-2">
          <Icon className="h-5 w-5 text-brand" aria-hidden />
          <h2 className="font-semibold text-fg">{title}</h2>
        </div>
        <dl className="space-y-2 text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4">
              <dt className="text-muted">{label}</dt>
              <dd className="tabular text-right font-mono text-fg">{value}</dd>
            </div>
          ))}
        </dl>
      </CardBody>
    </Card>
  )
}

function rule(m: MachineConfig): string {
  if (m.type === 'always_on') return 'Runs 24/7 (part of base load)'
  if (m.type === 'daily_quota') return `${m.hours_per_day} h every day`
  const due = m.due ? dateTime(m.due) : `${m.due_in_hours} h after plan start`
  const start = m.earliest_start ? `, not before ${dateTime(m.earliest_start)}` : m.start_in_hours ? `, not before +${m.start_in_hours} h` : ''
  return `${m.total_hours} h total, due ${due}${start}`
}

const TYPE_LABEL = { always_on: 'Always on', daily_quota: 'Daily quota', deadline: 'Deadline job' }

function MeterPeak() {
  const peak = useAsync(api.peak)
  const { runNow, running } = useRun()
  const { can } = useAuth()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  async function upload(file: File) {
    setBusy(true)
    setMessage(null)
    try {
      const next = await api.uploadMeter(file)
      await peak.reload()
      setMessage({ ok: true, text: `Read ${num(next.meter?.rows ?? 0)} readings. Highest draw in ${next.year}: ${kw(next.record_kw)}, costing ${eur(next.monthly_eur)} per month.` })
    } catch (err) {
      setMessage({ ok: false, text: err instanceof Error ? err.message : String(err) })
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }

  if (peak.error) return <ErrorView message={peak.error.message} onRetry={() => void peak.reload()} />
  if (!peak.data) return null
  const meter = peak.data.meter
  const action = can('meter.upload') && (
    <>
      <input
        ref={input}
        id="meter-file"
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) void upload(file)
        }}
      />
      <Button size="sm" onClick={() => input.current?.click()} disabled={busy}>
        <Upload className="h-4 w-4" aria-hidden /> {busy ? 'Reading…' : 'Upload meter data'}
      </Button>
    </>
  )
  return (
    <PeakPanel peak={peak.data} action={action}>
      <p className="text-xs text-muted">
        {meter
          ? `Meter data: ${num(meter.rows)} readings every ${meter.interval_minutes} min, ${dayLabel(meter.start)} – ${dayLabel(meter.end)}. `
          : 'No meter data uploaded yet. '}
        Upload the 15-minute load profile from the grid operator or supplier portal: a CSV with a <code>timestamp</code> column and <code>import_kw</code>{' '}
        (average kW) or <code>import_kwh</code> (kWh per 15 minutes). Comma or semicolon separated; times without a zone are read as German time.
      </p>
      {message && (
        <div role="status" className={`flex flex-wrap items-center gap-3 rounded-lg p-3 text-sm ${message.ok ? 'bg-positive-soft text-positive' : 'bg-danger-soft text-danger'}`}>
          <span>{message.text}</span>
          {message.ok && (
            <Button size="sm" variant="primary" onClick={() => void runNow()} disabled={running}>
              {running ? 'Planning…' : 'Re-plan with this peak'}
            </Button>
          )}
        </div>
      )}
    </PeakPanel>
  )
}

function SiteSpecs({ site, action }: { site: SiteConfig; action?: ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          <span className="font-medium text-fg">{site.name}</span> · {num(site.latitude, 2)}°N {num(site.longitude, 2)}°E · CO₂ {site.co2_kg_per_kwh} kg/kWh · plan email to{' '}
          {site.email_recipients.join(', ') || 'nobody'}
        </p>
        {action}
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Spec icon={Sun} title="Solar" rows={[['Peak power', `${num(site.solar.kwp)} kWp`], ['Tilt', `${site.solar.tilt}°`], ['Azimuth', `${site.solar.azimuth}° (0 = south)`], ['Performance ratio', pct(site.solar.performance_ratio)]]} />
        <Spec icon={Wind} title="Wind" rows={[['Rated power', power(site.wind.rated_kw)], ['Hub height', `${site.wind.hub_height_m} m`], ['Curve points', site.wind.power_curve.length]]} />
        <Spec icon={BatteryCharging} title="Battery" rows={[['Capacity', energy(site.battery.capacity_kwh)], ['Charge / discharge', `${power(site.battery.max_charge_kw)} / ${power(site.battery.max_discharge_kw)}`], ['Efficiency', pct(site.battery.efficiency)], ['Minimum charge', pct(site.battery.min_soc)]]} />
        <Spec icon={Cable} title="Grid" rows={[['Max import', power(site.grid.max_import_kw)], ['Max export', power(site.grid.max_export_kw)], ['Fees and levies', `€${num(site.grid.fee_eur_per_kwh, 3)}/kWh`], ['Export price', `€${num(site.grid.export_price_eur_per_kwh, 3)}/kWh`], ['Peak charge', `€${num(site.grid.peak_charge_eur_per_kw_year)}/kW·yr`], ['Peak from bill', kw(site.grid.peak_so_far_kw)]]} />
      </div>
    </section>
  )
}

interface MachineTableProps {
  machines: MachineConfig[]
  onEdit?: (m: MachineConfig) => void
  onDelete?: (m: MachineConfig) => void
}

function MachineTable({ machines, onEdit, onDelete }: MachineTableProps) {
  const [confirming, setConfirming] = useState<string | null>(null)
  if (!machines.length) return <p className="text-sm text-muted">No machines yet. Add the plant's big electrical loads, starting with those that run around the clock.</p>
  const editable = Boolean(onEdit && onDelete)
  return (
    <table className="w-full min-w-[680px] text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs text-muted">
          <th className="py-2 pr-4 font-medium">Machine</th>
          <th className="py-2 pr-4 font-medium">Type</th>
          <th className="py-2 pr-4 text-right font-medium">Power</th>
          <th className="py-2 pr-4 text-right font-medium">Shortest run</th>
          <th className="py-2 pr-4 font-medium">Rule</th>
          {editable && <th className="py-2 text-right font-medium"><span className="sr-only">Actions</span></th>}
        </tr>
      </thead>
      <tbody>
        {machines.map((m) => (
          <tr key={m.id} className="border-b border-border last:border-0">
            <td className="py-2.5 pr-4 font-medium text-fg">{m.name}</td>
            <td className="py-2.5 pr-4">
              <Badge tone={m.type === 'always_on' ? 'neutral' : m.type === 'deadline' ? 'warning' : 'info'}>{TYPE_LABEL[m.type]}</Badge>
            </td>
            <td className="tabular py-2.5 pr-4 text-right font-mono text-fg">{power(m.power_kw)}</td>
            <td className="tabular py-2.5 pr-4 text-right font-mono text-muted">{m.type === 'always_on' ? '–' : `${m.min_run_hours} h`}</td>
            <td className="py-2.5 pr-4 text-muted">{rule(m)}</td>
            {editable && (
              <td className="py-2 text-right whitespace-nowrap">
                {confirming === m.id ? (
                  <span className="inline-flex items-center gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setConfirming(null)}>Keep</Button>
                    <Button size="sm" className="border-danger/40 text-danger" onClick={() => { setConfirming(null); onDelete!(m) }}>
                      Delete {m.name}
                    </Button>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1">
                    <Button size="icon" variant="ghost" className="h-8 w-8" aria-label={`Edit ${m.name}`} onClick={() => onEdit!(m)}>
                      <Pencil className="h-4 w-4" aria-hidden />
                    </Button>
                    <Button size="icon" variant="ghost" className="h-8 w-8 hover:text-danger" aria-label={`Delete ${m.name}`} onClick={() => setConfirming(m.id)}>
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </span>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Step({ done, title, detail, error, warning, action }: { done: boolean; title: string; detail: ReactNode; error?: string | null; warning?: string | null; action?: ReactNode }) {
  return (
    <li className="flex flex-wrap items-start gap-3 py-3">
      <span
        aria-hidden
        className={cn('mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full', done ? 'bg-positive-soft text-positive' : error ? 'bg-danger-soft text-danger' : 'bg-surface-2 text-muted')}
      >
        {done ? <Check className="h-3.5 w-3.5" /> : error ? <CircleAlert className="h-3.5 w-3.5" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-fg">
          {title} <span className="sr-only">{done ? '(done)' : '(to do)'}</span>
        </p>
        <div className="text-xs text-muted">{detail}</div>
        {error && <p className="mt-1 text-xs text-danger">{error}</p>}
        {warning && <p className="mt-1 text-xs text-warning">{warning}</p>}
      </div>
      {action}
    </li>
  )
}

function LoadHistoryButton({ onUploaded }: { onUploaded: (s: SiteSetup) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const { notify } = useToast()
  async function upload(file: File) {
    setBusy(true)
    try {
      const next = await api.uploadLoadHistory(file)
      onUploaded(next)
      notify(`Load history saved: ${num(next.demand.rows ?? 0)} hours.`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  return (
    <>
      <input ref={input} id="load-history-file" type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])} />
      <Button size="sm" onClick={() => input.current?.click()} disabled={busy}>
        <Upload className="h-4 w-4" aria-hidden /> {busy ? 'Reading…' : 'Upload load history'}
      </Button>
    </>
  )
}

function Editor({ setup, onChange }: { setup: SiteSetup; onChange: (s: SiteSetup) => void }) {
  const { can } = useAuth()
  const { notify } = useToast()
  const { refresh, runNow, running } = useRun()
  const [siteOpen, setSiteOpen] = useState(false)
  const [machine, setMachine] = useState<MachineConfig | null | 'new'>(null)
  const canEdit = can('config.edit')
  const machines = setup.machine_data
  const missing = !setup.site.ok || !setup.machines.ok || !setup.demand.ok

  const applied = (next: SiteSetup, message: string) => {
    onChange(next)
    void refresh()
    notify(message)
  }
  const failure = (err: unknown) => (err instanceof Error ? err.message : String(err))

  async function saveSite(site: SiteConfig) {
    try {
      applied(await api.saveSite(site), 'Site settings saved. Re-plan to use them.')
      setSiteOpen(false)
      return null
    } catch (err) {
      return failure(err)
    }
  }
  async function saveMachines(next: MachineConfig[], message: string) {
    try {
      applied(await api.saveMachines(next), message)
      return null
    } catch (err) {
      return failure(err)
    }
  }
  async function saveMachine(m: MachineConfig) {
    const exists = machines.some((x) => x.id === m.id)
    const problem = await saveMachines(exists ? machines.map((x) => (x.id === m.id ? m : x)) : [...machines, m], `${m.name} ${exists ? 'updated' : 'added'}.`)
    if (!problem) setMachine(null)
    return problem
  }
  async function deleteMachine(m: MachineConfig) {
    if (machines.length === 1) return notify('Keep at least one machine. Add the replacement first, then delete this one.', 'error')
    const problem = await saveMachines(machines.filter((x) => x.id !== m.id), `${m.name} deleted.`)
    if (problem) notify(problem, 'error')
  }
  async function copySample() {
    try {
      applied(await api.copySample(), 'Copied the Holcim sample. Change the numbers to your plant.')
    } catch (err) {
      notify(failure(err), 'error')
    }
  }

  const demand = setup.demand
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title={setup.ready ? 'Your site is ready to plan' : 'Set up your site'}
          description={setup.ready ? 'Everything the planner needs is in place. Changes apply from the next plan.' : 'Three things are needed before GridShift can plan for your plant.'}
          action={
            setup.ready
              ? can('plan.run') && (
                  <Button variant="primary" size="sm" onClick={() => void runNow()} disabled={running}>
                    {running ? 'Planning…' : 'Re-plan now'}
                  </Button>
                )
              : canEdit && (
                  <Button size="sm" onClick={() => void copySample()}>
                    <Copy className="h-4 w-4" aria-hidden /> Start from the Holcim sample
                  </Button>
                )
          }
        />
        <CardBody className="pt-1">
          <ol className="divide-y divide-border">
            <Step
              done={setup.site.ok}
              title="1. Site details"
              detail={setup.site.ok ? setup.site.name : 'Location, grid connection, fees, peak charge, and any solar, wind or battery.'}
              error={setup.site.error}
              warning={
                setup.peak_unknown
                  ? "A peak charge is set but this year's highest kW is 0. Enter it from the bill or upload meter data, or every kW counts as a new peak."
                  : null
              }
              action={canEdit && <Button size="sm" onClick={() => setSiteOpen(true)}>{setup.site_data ? 'Edit site' : 'Add site details'}</Button>}
            />
            <Step
              done={setup.machines.ok}
              title="2. Machines"
              detail={setup.machines.ok ? `${setup.machines.count} machines` : 'Every large load: what it draws, and how many hours it must run.'}
              error={setup.machines.error}
              action={canEdit && <Button size="sm" onClick={() => setMachine('new')}><Plus className="h-4 w-4" aria-hidden /> Add machine</Button>}
            />
            <Step
              done={demand.ok}
              title="3. Load history"
              detail={
                demand.ok ? (
                  `${num(demand.rows ?? 0)} hours, ${dayLabel(demand.start!)} to ${dayLabel(demand.end!)}`
                ) : (
                  <>
                    At least one week of the always-on load, hourly: a CSV with <code>timestamp</code> and <code>load_kw</code> columns, comma or semicolon separated.
                  </>
                )
              }
              error={demand.error}
              action={canEdit && <LoadHistoryButton onUploaded={(next) => applied(next, 'Load history saved.')} />}
            />
            <Step
              done={setup.meter.ok}
              title="Optional: meter data"
              detail={setup.meter.ok ? `${num(setup.meter.rows ?? 0)} readings; sets this year's peak record` : "15-minute grid readings from the grid operator's portal. Upload them on the peak charge card once site details are in."}
            />
          </ol>
          <p className="mt-2 text-xs text-muted">German market price history is shared with the sample, so there is nothing to upload for prices.</p>
        </CardBody>
      </Card>

      {setup.site_data && (
        <>
          {setup.site_data.grid.peak_charge_eur_per_kw_year > 0 && <MeterPeak />}
          <SiteSpecs site={setup.site_data} action={canEdit && <Button size="sm" onClick={() => setSiteOpen(true)}><Pencil className="h-4 w-4" aria-hidden /> Edit site</Button>} />
        </>
      )}

      <Card>
        <CardHeader
          title="Machines"
          description="The planner moves machines with hours per day or a deadline to cheaper hours. Always-on machines stay put."
          action={canEdit && <Button size="sm" variant="primary" onClick={() => setMachine('new')}><Plus className="h-4 w-4" aria-hidden /> Add machine</Button>}
        />
        <CardBody className="overflow-x-auto">
          <MachineTable machines={machines} onEdit={canEdit ? (m) => setMachine(m) : undefined} onDelete={canEdit ? (m) => void deleteMachine(m) : undefined} />
        </CardBody>
      </Card>

      {!missing && !canEdit && <p className="text-xs text-muted">Only admins and planners can change the setup.</p>}

      {siteOpen && <SiteDialog open site={setup.site_data} onClose={() => setSiteOpen(false)} onSave={saveSite} />}
      {machine && (
        <MachineDialog
          open
          machine={machine === 'new' ? null : machine}
          takenIds={machines.map((m) => m.id)}
          onClose={() => setMachine(null)}
          onSave={saveMachine}
        />
      )}
    </div>
  )
}

function SampleView({ setup }: { setup: SiteSetup }) {
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm">
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden />
        <p className="text-fg">
          You're looking at the Holcim sample, which can't be edited here. Turn <span className="font-medium">Sample data</span> off in the sidebar to set up your own site and machines.
        </p>
      </div>
      {setup.site_data && setup.site_data.grid.peak_charge_eur_per_kw_year > 0 && <MeterPeak />}
      {setup.site_data && <SiteSpecs site={setup.site_data} />}
      <Card>
        <CardHeader title="Machines" description="From the Holcim sample: illustrative loads of a cement plant." />
        <CardBody className="overflow-x-auto">
          <MachineTable machines={setup.machine_data} />
        </CardBody>
      </Card>
    </div>
  )
}

export function Site() {
  const setup = useAsync(api.siteSetup)
  const [latest, setLatest] = useState<SiteSetup | null>(null)
  const data = latest ?? setup.data
  return (
    <PageLayout title="Site & machines" subtitle="Your plant, its machines and the history the planner learns from">
      {setup.loading && !data ? (
        <LoadingView />
      ) : setup.error && !data ? (
        <ErrorView message={setup.error.message} onRetry={() => void setup.reload()} />
      ) : (
        data && (data.editable ? <Editor setup={data} onChange={setLatest} /> : <SampleView setup={data} />)
      )}
    </PageLayout>
  )
}
