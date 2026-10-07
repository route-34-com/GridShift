import { cn } from '@/lib/utils'

/** Full GridShift emblem (sun, turbine, factory and rising bars), with a lighter factory in dark mode. */
export function Emblem({ className }: { className?: string }) {
  return (
    <span className={cn('relative block h-20 w-20 shrink-0', className)}>
      <img src="/brand/gridshift-mark.png" alt="GridShift" className="h-full w-full object-contain dark:hidden" />
      <img src="/brand/gridshift-mark-dark.png" alt="GridShift" className="hidden h-full w-full object-contain dark:block" />
    </span>
  )
}

/** GridShift mark: a lightning bolt on a solid brand tile, the same as the browser-tab icon. */
export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" role="img" aria-label="GridShift" className={cn('h-9 w-9 shrink-0', className)}>
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <path d="M17.5 5 8 18h7l-1.5 9L24 14h-7l.5-9z" fill="var(--brand-fg)" stroke="var(--brand-fg)" strokeWidth="1" strokeLinejoin="round" />
    </svg>
  )
}
