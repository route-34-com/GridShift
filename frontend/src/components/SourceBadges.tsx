import { Badge, type Tone } from '@/components/ui/badge'
import { Tooltip } from '@/components/ui/tooltip'

const LABELS: Record<string, string> = {
  price: 'Day-ahead price',
  site_weather: 'Site weather',
  national_weather: 'National weather',
}

const STATES: Record<string, { tone: Tone; text: string; help: string }> = {
  published: { tone: 'positive', text: 'live', help: 'Published EPEX day-ahead prices for the first day.' },
  live: { tone: 'positive', text: 'live', help: 'Fresh forecast from Open-Meteo.' },
  partial: { tone: 'warning', text: 'partial', help: 'Tomorrow is not fully published yet; missing hours are estimated.' },
  estimated: { tone: 'warning', text: 'estimated', help: 'Price source unavailable; all hours use the weather-based estimate.' },
  cached: { tone: 'warning', text: 'cached', help: 'Source unavailable; the last stored forecast is used.' },
  profile: { tone: 'warning', text: 'typical', help: 'No weather available; typical weekday-hour prices are used.' },
}

export function SourceBadges({ sources }: { sources: Record<string, string> }) {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(sources).map(([key, value]) => {
        const state = STATES[value] ?? { tone: 'neutral' as Tone, text: value, help: value }
        return (
          <Tooltip key={key} content={state.help}>
            <span tabIndex={0} className="cursor-help rounded-full">
              <Badge tone={state.tone}>
                <span className="text-muted">{LABELS[key] ?? key}</span> {state.text}
              </Badge>
            </span>
          </Tooltip>
        )
      })}
    </div>
  )
}
