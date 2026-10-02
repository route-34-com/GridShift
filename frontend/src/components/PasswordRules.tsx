import { Check, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'

const RULES = [
  { label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { label: 'Letters plus numbers or symbols', test: (p: string) => /[^0-9]/.test(p) && /[^a-zA-Z]/.test(p) },
]

export function passwordProblem(password: string): string | null {
  const failed = RULES.find((rule) => !rule.test(password))
  return failed ? failed.label : null
}

export function PasswordRules({ password }: { password: string }) {
  return (
    <ul className="space-y-1 text-xs" aria-label="Password rules">
      {RULES.map((rule) => {
        const ok = rule.test(password)
        const Icon = ok ? Check : Circle
        return (
          <li key={rule.label} className={cn('flex items-center gap-2', ok ? 'text-positive' : 'text-muted')}>
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {rule.label}
          </li>
        )
      })}
    </ul>
  )
}
