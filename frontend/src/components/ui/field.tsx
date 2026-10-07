import * as RadixSelect from '@radix-ui/react-select'
import { Check, ChevronDown, Eye, EyeOff } from 'lucide-react'
import { useId, useState, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

const CONTROL =
  'h-10 w-full rounded-md border border-border bg-surface px-3 text-sm text-fg placeholder:text-muted/70 transition-colors duration-200 focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30 disabled:cursor-not-allowed disabled:opacity-60'

interface FieldProps {
  label: string
  hint?: ReactNode
  error?: string | null
  children: (id: string) => ReactNode
}

export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId()
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-fg">
        {label}
      </label>
      {children(id)}
      {error ? <p className="text-xs text-danger">{error}</p> : hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  )
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(CONTROL, className)} {...props} />
}

export function PasswordInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  const [shown, setShown] = useState(false)
  return (
    <div className="relative">
      <input type={shown ? 'text' : 'password'} className={cn(CONTROL, 'pr-10', className)} {...props} />
      <button
        type="button"
        onClick={() => setShown((s) => !s)}
        aria-label={shown ? 'Hide password' : 'Show password'}
        className="absolute inset-y-0 right-0 flex w-10 cursor-pointer items-center justify-center text-muted hover:text-fg"
      >
        {shown ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
      </button>
    </div>
  )
}

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps {
  value: string
  onValueChange: (value: string) => void
  options: SelectOption[]
  id?: string
  'aria-label'?: string
  disabled?: boolean
  /** Sizes the trigger; full width by default. */
  className?: string
}

/** Radix needs a non-empty value per item, so an empty choice (e.g. "Everyone") travels under this stand-in. */
const EMPTY = '__empty__'

/** The one dropdown used across the app: a themed trigger and list with keyboard support. */
export function Select({ value, onValueChange, options, id, disabled, className, ...aria }: SelectProps) {
  return (
    <RadixSelect.Root value={value === '' ? EMPTY : value} onValueChange={(v) => onValueChange(v === EMPTY ? '' : v)} disabled={disabled}>
      <RadixSelect.Trigger
        id={id}
        aria-label={aria['aria-label']}
        className={cn(CONTROL, 'flex cursor-pointer items-center justify-between gap-2 text-left hover:bg-surface-2 data-[placeholder]:text-muted', className)}
      >
        <span className="truncate">
          <RadixSelect.Value />
        </span>
        <RadixSelect.Icon>
          <ChevronDown className="h-4 w-4 shrink-0 text-muted" aria-hidden />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          sideOffset={6}
          className="z-50 max-h-(--radix-select-content-available-height) min-w-(--radix-select-trigger-width) overflow-hidden rounded-lg border border-border bg-surface-solid p-1 text-sm text-fg shadow-xl"
        >
          <RadixSelect.Viewport>
            {options.map((o) => (
              <RadixSelect.Item
                key={o.value}
                value={o.value === '' ? EMPTY : o.value}
                className="relative flex cursor-pointer items-center rounded-md py-2 pr-8 pl-2.5 outline-none select-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-surface-2 data-[state=checked]:font-medium"
              >
                <RadixSelect.ItemText>{o.label}</RadixSelect.ItemText>
                <RadixSelect.ItemIndicator className="absolute right-2.5 text-brand">
                  <Check className="h-4 w-4" aria-hidden />
                </RadixSelect.ItemIndicator>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  )
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(CONTROL, 'h-auto py-2', className)} {...props} />
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
      {message}
    </p>
  )
}
