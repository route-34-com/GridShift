import { LoaderIcon } from 'lucide-react'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

/** A spinning loader icon; announced as "Loading" unless it sits inside a control that says so itself. */
export function Spinner({ className, ...props }: ComponentProps<'svg'>) {
  return <LoaderIcon role="status" aria-label="Loading" data-spinner className={cn('size-4 animate-spin', className)} {...props} />
}

/** A centered spinner with a short label, for content that is still loading. */
export function Loader({ label = 'Loading…', className }: { label?: string; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={cn('flex min-h-40 flex-col items-center justify-center gap-3 text-sm text-muted', className)}>
      <Spinner aria-hidden role={undefined} aria-label={undefined} className="size-6 text-brand" />
      <span>{label}</span>
    </div>
  )
}
