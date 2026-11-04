import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { CONTROL, Select } from '@/components/ui/field'
import { cn } from '@/lib/utils'

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const WEEKDAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

const pad = (n: number) => String(n).padStart(2, '0')
const iso = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`

function parse(value: string): { y: number; m: number; d: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  return match ? { y: Number(match[1]), m: Number(match[2]) - 1, d: Number(match[3]) } : null
}

function todayIso(): string {
  const now = new Date()
  return iso(now.getFullYear(), now.getMonth(), now.getDate())
}

/** "04 Nov 2026" for a YYYY-MM-DD value. */
export function formatDay(value: string): string {
  const p = parse(value)
  return p ? `${pad(p.d)} ${SHORT[p.m]} ${p.y}` : ''
}

interface DatePickerProps {
  value: string
  onChange: (value: string) => void
  id?: string
  min?: string
  max?: string
  placeholder?: string
  'aria-label'?: string
  /** Hide the clear control, for fields that always need a date. */
  required?: boolean
}

/** A calendar dropdown for a YYYY-MM-DD value, weeks starting on Monday. */
export function DatePicker({ value, onChange, id, min, max, placeholder = 'Any date', required = false, ...aria }: DatePickerProps) {
  const [open, setOpen] = useState(false)
  const [above, setAbove] = useState(false)
  const selected = parse(value)
  const start = selected ?? parse(todayIso())!
  const [view, setView] = useState({ y: start.y, m: start.m })
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false)
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation()
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', escape, true)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', escape, true)
    }
  }, [open])

  const days = useMemo(() => {
    const first = new Date(view.y, view.m, 1)
    const offset = (first.getDay() + 6) % 7
    return Array.from({ length: 42 }, (_, i) => {
      const date = new Date(view.y, view.m, 1 - offset + i)
      return { value: iso(date.getFullYear(), date.getMonth(), date.getDate()), day: date.getDate(), inMonth: date.getMonth() === view.m }
    })
  }, [view])

  const today = todayIso()
  const outside = (day: string) => Boolean((min && day < min) || (max && day > max))
  const shift = (months: number) => setView((v) => {
    const next = new Date(v.y, v.m + months, 1)
    return { y: next.getFullYear(), m: next.getMonth() }
  })
  const pick = (day: string) => {
    onChange(day)
    setOpen(false)
  }
  const toggle = () => {
    if (!open) {
      setView({ y: start.y, m: start.m })
      const rect = root.current?.getBoundingClientRect()
      setAbove(rect ? window.innerHeight - rect.bottom < 340 && rect.top > 340 : false)
    }
    setOpen((o) => !o)
  }

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        id={id}
        aria-label={aria['aria-label']}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={toggle}
        className={cn(CONTROL, 'flex cursor-pointer items-center justify-between gap-2 text-left hover:bg-surface-2')}
      >
        <span className={cn('truncate', !value && 'text-muted/80')}>{value ? formatDay(value) : placeholder}</span>
        <CalendarDays className="h-4 w-4 shrink-0 text-muted" aria-hidden />
      </button>
      {value && !required && (
        <button
          type="button"
          aria-label="Clear date"
          onClick={() => onChange('')}
          className="absolute inset-y-0 right-8 my-auto flex h-6 w-6 cursor-pointer items-center justify-center rounded text-muted hover:bg-surface-2 hover:text-fg"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      )}
      {open && (
        <div
          role="dialog"
          aria-label="Choose a date"
          className={cn(
            'absolute right-0 z-50 w-[17.5rem] rounded-xl border border-border bg-surface-solid p-3 text-fg shadow-[0_12px_32px_-10px_rgb(0_0_0/0.25)]',
            above ? 'bottom-full mb-1.5' : 'top-full mt-1.5',
          )}
        >
          <div className="mb-2 flex items-center justify-between">
            <p className="pl-1 text-sm font-semibold">
              {MONTHS[view.m]} <span className="font-normal text-muted">{view.y}</span>
            </p>
            <div className="flex gap-0.5">
              <button type="button" aria-label="Previous month" onClick={() => shift(-1)} className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-fg">
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </button>
              <button type="button" aria-label="Next month" onClick={() => shift(1)} className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-fg">
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </div>
          <div className="grid grid-cols-7 gap-0.5 text-center">
            {WEEKDAYS.map((w) => (
              <span key={w} className="py-1 text-[11px] font-medium text-muted">
                {w}
              </span>
            ))}
            {days.map((d) => {
              const isSelected = d.value === value
              const disabled = outside(d.value)
              return (
                <button
                  key={d.value}
                  type="button"
                  disabled={disabled}
                  aria-label={formatDay(d.value)}
                  aria-pressed={isSelected}
                  onClick={() => pick(d.value)}
                  className={cn(
                    'tabular h-8 cursor-pointer rounded-md text-[13px] transition-colors disabled:cursor-not-allowed disabled:opacity-30',
                    isSelected ? 'bg-primary font-semibold text-primary-fg' : 'hover:bg-surface-2',
                    !isSelected && !d.inMonth && 'text-muted/60',
                    !isSelected && d.value === today && 'font-semibold text-brand ring-1 ring-brand/40 ring-inset',
                  )}
                >
                  {d.day}
                </button>
              )
            })}
          </div>
          <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
            {required ? <span /> : (
              <button type="button" onClick={() => pick('')} className="cursor-pointer rounded-md px-2 py-1 text-[13px] text-muted hover:bg-surface-2 hover:text-fg">
                Clear
              </button>
            )}
            <button type="button" disabled={outside(today)} onClick={() => pick(today)} className="cursor-pointer rounded-md px-2 py-1 text-[13px] font-medium text-brand hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-40">
              Today
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

const TIMES = Array.from({ length: 96 }, (_, i) => {
  const t = `${pad(Math.floor(i / 4))}:${pad((i % 4) * 15)}`
  return { value: t, label: t }
})

interface DateTimePickerProps {
  value: string
  onChange: (value: string) => void
  'aria-label'?: string
}

/** A date and a 15-minute time (German time) for a YYYY-MM-DDTHH:MM value. */
export function DateTimePicker({ value, onChange, ...aria }: DateTimePickerProps) {
  const [day, time] = value ? value.split('T') : ['', '']
  const slot = time ? time.slice(0, 5) : '00:00'
  const known = TIMES.some((t) => t.value === slot)
  const options = known ? TIMES : [{ value: slot, label: slot }, ...TIMES]
  return (
    <div className="grid grid-cols-[1fr_6.5rem] gap-2">
      <DatePicker value={day} onChange={(d) => onChange(d ? `${d}T${slot}` : '')} placeholder="Pick a date" required aria-label={aria['aria-label'] ? `${aria['aria-label']}: date` : 'Date'} />
      <Select value={slot} onValueChange={(t) => onChange(`${day || todayIso()}T${t}`)} options={options} aria-label={aria['aria-label'] ? `${aria['aria-label']}: time` : 'Time'} />
    </div>
  )
}
