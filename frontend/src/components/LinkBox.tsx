import { Check, Copy } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { LinkResult } from '@/lib/types'

export function LinkBox({ result, sentTo }: { result: LinkResult; sentTo: string }) {
  const [copied, setCopied] = useState(false)
  if (result.emailed) {
    return (
      <p className="rounded-lg border border-positive/30 bg-positive-soft px-3 py-2 text-sm text-fg">
        Email sent to <span className="font-medium">{sentTo}</span>.
      </p>
    )
  }
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.link ?? '')
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }
  return (
    <div className="space-y-2 rounded-lg border border-warning/30 bg-warning-soft p-3 text-sm">
      <p className="text-fg">{result.warning}</p>
      <div className="flex gap-2">
        <input readOnly value={result.link} aria-label="Link" onFocus={(e) => e.currentTarget.select()} className="h-9 min-w-0 flex-1 rounded-md border border-border bg-surface px-2 font-mono text-xs text-fg" />
        <Button size="sm" onClick={() => void copy()}>
          {copied ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
    </div>
  )
}
