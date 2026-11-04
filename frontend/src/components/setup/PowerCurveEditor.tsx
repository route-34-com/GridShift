import { Plus, Trash2, Wand2 } from 'lucide-react'
import type { ClipboardEvent } from 'react'
import { PowerCurveChart } from '@/components/charts/PowerCurveChart'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/field'
import { checkCurve, parseCurveText, toCurveRows, typicalCurve, type CurveRow } from '@/lib/weather'
import { cn } from '@/lib/utils'

interface PowerCurveEditorProps {
  rows: CurveRow[]
  ratedKw: number
  onChange: (rows: CurveRow[]) => void
}

/** Edit a turbine power curve as a table, with a live chart of what the planner will use. */
export function PowerCurveEditor({ rows, ratedKw, onChange }: PowerCurveEditorProps) {
  const { curve, errors, notes } = checkCurve(rows, ratedKw)

  const set = (i: number, key: keyof CurveRow, value: string) => onChange(rows.map((r, j) => (j === i ? { ...r, [key]: value } : r)))

  function paste(i: number, event: ClipboardEvent<HTMLInputElement>) {
    const text = event.clipboardData.getData('text')
    if (!/\n/.test(text.trim())) return
    const pasted = parseCurveText(text)
    if (!pasted.length) return
    event.preventDefault()
    onChange([...rows.slice(0, i), ...pasted])
  }

  function addRow() {
    const last = curve[curve.length - 1]
    onChange([...rows, { speed: last ? String(last[0] + 1) : '', kw: '' }])
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-border bg-surface p-2">
        {curve.length >= 2 ? (
          <PowerCurveChart curve={curve} ratedKw={ratedKw} height={220} />
        ) : (
          <p className="flex h-[120px] items-center justify-center px-4 text-center text-sm text-muted">Add at least two points to see the curve.</p>
        )}
      </div>

      <div className="max-h-72 overflow-y-auto rounded-lg border border-border">
        <table className="w-full border-separate border-spacing-0 text-sm">
          <thead className="sticky top-0 z-10 bg-surface-solid bg-[image:linear-gradient(var(--surface-2),var(--surface-2))] shadow-[0_1px_0_var(--border)]">
            <tr className="text-left text-xs text-muted">
              <th className="w-10 py-2 pl-3 font-medium">#</th>
              <th className="py-2 pr-2 font-medium">Wind speed (m/s)</th>
              <th className="py-2 pr-2 font-medium">Power (kW)</th>
              <th className="w-12 py-2 pr-2"><span className="sr-only">Remove</span></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const message = errors[i] ?? notes[i]
              return (
                <tr key={i} className="align-top [&>td]:border-t [&>td]:border-border">
                  <td className="py-2 pl-3 text-xs leading-9 text-muted tabular">{i + 1}</td>
                  <td className="py-1.5 pr-2">
                    <Input
                      aria-label={`Wind speed, row ${i + 1}`}
                      inputMode="decimal"
                      value={row.speed}
                      onChange={(e) => set(i, 'speed', e.target.value)}
                      onPaste={(e) => paste(i, e)}
                      aria-invalid={Boolean(errors[i])}
                      className={cn('h-9 tabular', errors[i] && 'border-danger')}
                    />
                  </td>
                  <td className="py-1.5 pr-2">
                    <Input
                      aria-label={`Power, row ${i + 1}`}
                      inputMode="decimal"
                      value={row.kw}
                      onChange={(e) => set(i, 'kw', e.target.value)}
                      onPaste={(e) => paste(i, e)}
                      aria-invalid={Boolean(errors[i])}
                      className={cn('h-9 tabular', errors[i] && 'border-danger')}
                    />
                    {message && <p className={cn('mt-1 text-xs', errors[i] ? 'text-danger' : 'text-warning')}>{message}</p>}
                  </td>
                  <td className="py-1.5 pr-2 text-right">
                    <Button size="sm" variant="ghost" className="h-9 w-9 px-0" aria-label={`Remove row ${i + 1}`} onClick={() => onChange(rows.filter((_, j) => j !== i))}>
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={addRow}>
          <Plus className="h-4 w-4" aria-hidden /> Add point
        </Button>
        <Button size="sm" variant="ghost" disabled={ratedKw <= 0} onClick={() => onChange(toCurveRows(typicalCurve(ratedKw)))} title={ratedKw <= 0 ? 'Enter the rated power first' : undefined}>
          <Wand2 className="h-4 w-4" aria-hidden /> Use a typical curve
        </Button>
      </div>
      <p className="text-xs text-muted">
        From the turbine datasheet, slowest wind first. Paste two columns copied from a spreadsheet or PDF into any cell to fill the table. Between points the planner draws a straight line;
        above the last point output is zero.
      </p>
    </div>
  )
}
