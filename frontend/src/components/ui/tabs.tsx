import type { LucideIcon } from 'lucide-react'
import { useRef, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface TabItem<T extends string> {
  id: T
  label: string
  icon: LucideIcon
  /** Headline figure shown on the tab, e.g. the week's average price. */
  value?: ReactNode
  color: string
}

interface MetricTabsProps<T extends string> {
  label: string
  items: TabItem<T>[]
  active: T
  onChange: (id: T) => void
  idPrefix: string
}

/** Tabs drawn as metric tiles; arrow keys move between them. */
export function MetricTabs<T extends string>({ label, items, active, onChange, idPrefix }: MetricTabsProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])
  const onKey = (event: KeyboardEvent, index: number) => {
    const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    event.preventDefault()
    const next = (index + step + items.length) % items.length
    onChange(items[next].id)
    refs.current[next]?.focus()
  }
  return (
    <div role="tablist" aria-label={label} className="grid grid-cols-3 gap-2">
      {items.map((item, index) => {
        const selected = item.id === active
        const Icon = item.icon
        return (
          <button
            key={item.id}
            ref={(el) => {
              refs.current[index] = el
            }}
            type="button"
            role="tab"
            id={`${idPrefix}-tab-${item.id}`}
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => onKey(e, index)}
            className={cn(
              'group relative flex min-w-0 cursor-pointer items-center gap-3 overflow-hidden rounded-lg border px-3 py-2.5 text-left sm:px-4 sm:py-3 transition-[background-color,border-color,box-shadow] duration-200',
              selected ? 'border-transparent bg-surface shadow-(--glow) ring-1 ring-brand/40' : 'border-transparent bg-surface-2 hover:bg-surface hover:ring-1 hover:ring-border',
            )}
          >
            <span
              aria-hidden
              className="hidden h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors sm:flex"
              style={{ background: `color-mix(in oklab, ${item.color} ${selected ? 22 : 12}%, transparent)`, color: item.color }}
            >
              <Icon className="h-[18px] w-[18px]" />
            </span>
            <span className="min-w-0">
              <span className={cn('block text-sm font-medium', selected ? 'text-fg' : 'text-muted group-hover:text-fg')}>{item.label}</span>
              {item.value != null && <span className="tabular block truncate  text-[11px] text-muted sm:text-xs">{item.value}</span>}
            </span>
            <span aria-hidden className={cn('absolute inset-x-3 bottom-0 sm:inset-x-4 h-[3px] rounded-t-full transition-opacity', selected ? 'opacity-100' : 'opacity-0')} style={{ background: item.color }} />
          </button>
        )
      })}
    </div>
  )
}
