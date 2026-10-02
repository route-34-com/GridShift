import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { MenuContent, MenuItem, MenuLabel, MenuRoot, MenuSeparator, MenuTrigger } from '@/components/ui/menu'
import { useRun } from '@/hooks/RunContext'
import { useToast } from '@/hooks/Toasts'

export interface ExportOption {
  label: string
  formats: ('csv' | 'xlsx')[]
  run: (format: 'csv' | 'xlsx') => Promise<string>
}

interface ExportMenuProps {
  options: ExportOption[]
  label?: string
}

const ICONS = { csv: FileText, xlsx: FileSpreadsheet }
const NAMES = { csv: 'CSV', xlsx: 'Excel' }

export function ExportMenu({ options, label = 'Export' }: ExportMenuProps) {
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)

  const start = async (option: ExportOption, format: 'csv' | 'xlsx') => {
    setBusy(true)
    try {
      const file = await option.run(format)
      notify(`Downloaded ${file}`)
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <MenuRoot>
      <MenuTrigger asChild>
        <Button disabled={busy}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Download className="h-4 w-4" aria-hidden />}
          {label}
        </Button>
      </MenuTrigger>
      <MenuContent>
        {options.map((option, index) => (
          <div key={option.label}>
            {index > 0 && <MenuSeparator />}
            <MenuLabel>{option.label}</MenuLabel>
            {option.formats.map((format) => {
              const Icon = ICONS[format]
              return (
                <MenuItem key={format} onSelect={() => void start(option, format)}>
                  <Icon className="h-4 w-4 text-muted" aria-hidden />
                  {NAMES[format]} (.{format})
                </MenuItem>
              )
            })}
          </div>
        ))}
      </MenuContent>
    </MenuRoot>
  )
}

export function PlanExportMenu(props: ExportMenuProps) {
  const { data } = useRun()
  if (!data) return null
  return <ExportMenu {...props} />
}
