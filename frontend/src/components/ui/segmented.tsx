import { cn } from '@/lib/utils'

interface SegmentedProps<T extends string> {
  label: string
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
  size?: 'sm' | 'md'
}

/** A small set of mutually exclusive choices shown side by side, e.g. 24h / 12h. */
export function Segmented<T extends string>({ label, value, options, onChange, size = 'md' }: SegmentedProps<T>) {
  const small = size === 'sm'
  return (
    <div role="radiogroup" aria-label={label} className={cn('inline-flex border border-border bg-surface-2', small ? 'rounded-md p-0.5 text-[11px]' : 'rounded-lg p-0.5 text-sm')}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'cursor-pointer font-medium transition-colors duration-200',
            small ? 'rounded px-1.5 py-0.5' : 'rounded-md px-3 py-1.5',
            value === o.value ? 'bg-surface-solid text-fg shadow-sm' : 'text-muted hover:text-fg',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
