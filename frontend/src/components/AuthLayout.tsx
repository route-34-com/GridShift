import { Moon, Sun } from 'lucide-react'
import type { ReactNode } from 'react'
import { Emblem } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useTheme } from '@/hooks/useTheme'

interface AuthLayoutProps {
  title: string
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
}

function Brand({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="flex items-center gap-4">
        <Emblem />
        <div>
          <p className="font-display text-3xl leading-tight font-semibold text-nav-fg">GridShift</p>
          <p className="text-sm text-nav-muted">Smart energy scheduling for industry</p>
        </div>
      </div>
    </div>
  )
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  const [theme, toggle] = useTheme()
  return (
    <div className="relative flex min-h-screen bg-bg">
      <div className="backdrop" aria-hidden />
      <div className="nav-surface relative z-[1] hidden w-[44%] max-w-[640px] flex-col justify-between overflow-hidden border-r p-10 lg:flex">
        <Brand />
        <div className="max-w-md">
          <p className="font-display text-[44px] leading-[1.08] font-semibold tracking-[-0.03em] text-nav-fg">
            Run the right machines at the <span className="text-brand">right hour.</span>
          </p>
          <p className="mt-4 text-base leading-relaxed text-nav-muted">
            Day-ahead prices, a 7-day weather outlook and an optimizer that plans every machine and the battery for the lowest energy bill.
          </p>
        </div>
        <p className="text-sm text-nav-muted">Plans your plant’s week around German power prices and on-site solar and wind.</p>
        <svg aria-hidden className="pointer-events-none absolute -right-24 -bottom-24 h-96 w-96 text-mark/10" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="48" fill="none" stroke="currentColor" strokeWidth="2" />
          <circle cx="50" cy="50" r="34" fill="none" stroke="currentColor" strokeWidth="2" />
          <circle cx="50" cy="50" r="20" fill="none" stroke="currentColor" strokeWidth="2" />
        </svg>
      </div>
      <main className="relative z-[1] flex flex-1 items-center justify-center px-4 py-10">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="absolute top-4 right-4"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
        </Button>
        <div className="w-full max-w-[420px]">
          <Brand className="mb-8 lg:hidden" />
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
