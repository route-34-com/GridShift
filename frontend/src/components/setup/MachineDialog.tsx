import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { Field, FormError, Input, Select } from '@/components/ui/field'
import { slug } from '@/lib/machines'
import type { MachineConfig } from '@/lib/types'

type Kind = MachineConfig['type']

const KINDS: { value: Kind; label: string; hint: string }[] = [
  { value: 'always_on', label: 'Always on', hint: 'Runs around the clock, like a kiln line. Part of the base load; the planner never moves it.' },
  { value: 'daily_quota', label: 'Hours every day', hint: 'Needs a set number of hours each day, like a cement mill. The planner picks the cheapest hours.' },
  { value: 'deadline', label: 'Job with a deadline', hint: 'Needs a total number of hours before a date, like a special order.' },
]

interface Draft {
  name: string
  type: Kind
  power: string
  minRun: string
  hoursPerDay: string
  totalHours: string
  dueMode: 'date' | 'hours'
  due: string
  dueIn: string
  startMode: 'none' | 'date' | 'hours'
  start: string
  startIn: string
}

const local = (iso?: string | null) => (iso ? iso.slice(0, 16) : '')

function draftFrom(m: MachineConfig | null): Draft {
  return {
    name: m?.name ?? '',
    type: m?.type ?? 'daily_quota',
    power: m ? String(m.power_kw) : '',
    minRun: String(m?.min_run_hours ?? 1),
    hoursPerDay: String(m?.hours_per_day ?? 8),
    totalHours: String(m?.total_hours ?? 10),
    dueMode: m?.due_in_hours != null ? 'hours' : 'date',
    due: local(m?.due),
    dueIn: String(m?.due_in_hours ?? 72),
    startMode: m?.earliest_start ? 'date' : m?.start_in_hours != null ? 'hours' : 'none',
    start: local(m?.earliest_start),
    startIn: String(m?.start_in_hours ?? 0),
  }
}

/** Turn the form into the machine the planner reads; returns an error message instead when something is missing. */
function build(d: Draft, id: string): MachineConfig | string {
  const power = Number(d.power)
  if (!d.name.trim()) return 'Give the machine a name.'
  if (!(power > 0)) return 'Power must be more than 0 kW.'
  const base = { id, name: d.name.trim(), power_kw: power, min_run_hours: 1 }
  if (d.type === 'always_on') return { ...base, type: 'always_on' }
  const minRun = Math.round(Number(d.minRun))
  if (!(minRun >= 1 && minRun <= 24)) return 'Shortest run must be 1 to 24 hours.'
  if (d.type === 'daily_quota') {
    const hours = Math.round(Number(d.hoursPerDay))
    if (!(hours >= 1 && hours <= 24)) return 'Hours per day must be 1 to 24.'
    if (minRun > hours) return 'The shortest run cannot be longer than the hours per day.'
    return { ...base, type: 'daily_quota', min_run_hours: minRun, hours_per_day: hours }
  }
  const total = Math.round(Number(d.totalHours))
  if (!(total >= 1)) return 'Total hours must be at least 1.'
  if (minRun > total) return 'The shortest run cannot be longer than the total hours.'
  const job: MachineConfig = { ...base, type: 'deadline', min_run_hours: minRun, total_hours: total }
  if (d.dueMode === 'date') {
    if (!d.due) return 'Pick the due date and time.'
    job.due = `${d.due}:00`
  } else {
    const hours = Math.round(Number(d.dueIn))
    if (!(hours >= 1)) return 'Due in must be at least 1 hour.'
    job.due_in_hours = hours
  }
  if (d.startMode === 'date' && d.start) job.earliest_start = `${d.start}:00`
  if (d.startMode === 'hours') job.start_in_hours = Math.max(0, Math.round(Number(d.startIn)))
  return job
}

interface MachineDialogProps {
  open: boolean
  machine: MachineConfig | null
  takenIds: string[]
  onClose: () => void
  onSave: (machine: MachineConfig) => Promise<string | null>
}

export function MachineDialog({ open, machine, takenIds, onClose, onSave }: MachineDialogProps) {
  const [draft, setDraft] = useState<Draft>(() => draftFrom(machine))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (patch: Partial<Draft>) => setDraft((d) => ({ ...d, ...patch }))
  const kind = KINDS.find((k) => k.value === draft.type)!

  async function submit(event: FormEvent) {
    event.preventDefault()
    const built = build(draft, machine?.id ?? slug(draft.name, takenIds))
    if (typeof built === 'string') return setError(built)
    setBusy(true)
    const problem = await onSave(built)
    setBusy(false)
    if (problem) setError(problem)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => !next && onClose()}
      title={machine ? `Edit ${machine.name}` : 'Add a machine'}
      description="Power is what the machine draws while running. Times are German time."
      wide
    >
      <form id="machine-form" onSubmit={(e) => void submit(e)} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name">{(id) => <Input id={id} value={draft.name} onChange={(e) => set({ name: e.target.value })} placeholder="Cement mill 1" autoFocus />}</Field>
          <Field label="Power (kW)">
            {(id) => <Input id={id} type="number" min="0" step="any" inputMode="decimal" value={draft.power} onChange={(e) => set({ power: e.target.value })} placeholder="4500" />}
          </Field>
        </div>
        <Field label="How it runs" hint={kind.hint}>
          {(id) => (
            <Select id={id} value={draft.type} onChange={(e) => set({ type: e.target.value as Kind })}>
              {KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </Select>
          )}
        </Field>

        {draft.type !== 'always_on' && (
          <div className="grid gap-4 sm:grid-cols-2">
            {draft.type === 'daily_quota' ? (
              <Field label="Hours every day">
                {(id) => <Input id={id} type="number" min="1" max="24" value={draft.hoursPerDay} onChange={(e) => set({ hoursPerDay: e.target.value })} />}
              </Field>
            ) : (
              <Field label="Total hours needed">
                {(id) => <Input id={id} type="number" min="1" value={draft.totalHours} onChange={(e) => set({ totalHours: e.target.value })} />}
              </Field>
            )}
            <Field label="Shortest run (hours)" hint="Once started, it keeps running at least this long.">
              {(id) => <Input id={id} type="number" min="1" max="24" value={draft.minRun} onChange={(e) => set({ minRun: e.target.value })} />}
            </Field>
          </div>
        )}

        {draft.type === 'deadline' && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Due">
              {(id) => (
                <div className="space-y-2">
                  <Select id={id} value={draft.dueMode} onChange={(e) => set({ dueMode: e.target.value as Draft['dueMode'] })}>
                    <option value="date">On a date and time</option>
                    <option value="hours">Hours after the plan starts</option>
                  </Select>
                  {draft.dueMode === 'date' ? (
                    <Input type="datetime-local" aria-label="Due date and time" value={draft.due} onChange={(e) => set({ due: e.target.value })} />
                  ) : (
                    <Input type="number" min="1" aria-label="Due in hours" value={draft.dueIn} onChange={(e) => set({ dueIn: e.target.value })} />
                  )}
                </div>
              )}
            </Field>
            <Field label="Earliest start">
              {(id) => (
                <div className="space-y-2">
                  <Select id={id} value={draft.startMode} onChange={(e) => set({ startMode: e.target.value as Draft['startMode'] })}>
                    <option value="none">Any time</option>
                    <option value="date">Not before a date and time</option>
                    <option value="hours">Hours after the plan starts</option>
                  </Select>
                  {draft.startMode === 'date' && <Input type="datetime-local" aria-label="Earliest start" value={draft.start} onChange={(e) => set({ start: e.target.value })} />}
                  {draft.startMode === 'hours' && <Input type="number" min="0" aria-label="Start after hours" value={draft.startIn} onChange={(e) => set({ startIn: e.target.value })} />}
                </div>
              )}
            </Field>
          </div>
        )}
        <FormError message={error} />
        <div className="flex justify-end gap-2 border-t border-border pt-4">
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? 'Saving…' : machine ? 'Save machine' : 'Add machine'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
