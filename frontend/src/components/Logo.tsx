import { cn } from '@/lib/utils'

/** GridShift mark: a load profile stepping down into cheaper hours, on a solid brand tile. */
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" role="img" aria-label="GridShift" className={cn('h-9 w-9 shrink-0', className)}>
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <path d="M7 10.5h6v5.5h6v5.5h6" fill="none" stroke="var(--brand-fg)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="25" cy="21.5" r="2.2" fill="var(--brand-fg)" />
    </svg>
  )
}
