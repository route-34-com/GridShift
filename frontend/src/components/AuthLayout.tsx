import { Zap } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'

interface AuthLayoutProps {
  title: string
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="relative flex min-h-screen bg-bg">
      <div className="backdrop" aria-hidden />
      <div className="relative z-[1] hidden w-[44%] max-w-[640px] flex-col justify-between overflow-hidden bg-nav p-10 text-nav-fg lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="logo-glow flex h-9 w-9 items-center justify-center rounded-lg">
            <Zap className="h-5 w-5 text-white" fill="currentColor" aria-hidden />
          </div>
          <span className="text-lg font-semibold">GridShift</span>
        </div>
        <div className="max-w-md">
          <p className="font-display text-[44px] leading-[1.08] font-semibold tracking-[-0.03em]">Run the right machines at the <span className="text-gradient">right hour.</span></p>
          <p className="mt-4 text-base leading-relaxed text-white/75">
            Day-ahead prices, a 7-day weather outlook and an optimizer that plans every machine and the battery for the lowest energy bill.
          </p>
        </div>
        <p className="text-sm text-white/60">Smart energy scheduling for industry</p>
        <svg aria-hidden className="pointer-events-none absolute -right-24 -bottom-24 h-96 w-96 text-mark/10" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="none" stroke="currentColor" strokeWidth="2" />
          <circle cx="50" cy="50" r="34" fill="none" stroke="currentColor" strokeWidth="2" />
          <circle cx="50" cy="50" r="20" fill="none" stroke="currentColor" strokeWidth="2" />
        </svg>
      </div>
      <main className="relative z-[1] flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-[420px]">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-nav">
              <Zap className="h-5 w-5 text-mark" fill="currentColor" aria-hidden />
            </div>
            <span className="text-lg font-semibold text-fg">GridShift</span>
          </div>
          <Card className="p-6 sm:p-8">
            <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
            {subtitle && <div className="mt-1.5 text-sm text-muted">{subtitle}</div>}
            <div className="mt-6">{children}</div>
          </Card>
          {footer && <div className="mt-6 text-center text-sm text-muted">{footer}</div>}
        </div>
      </main>
    </div>
  )
}
