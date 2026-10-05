const TZ = 'Europe/Berlin'

const euro0 = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 })
const euro2 = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 })
const number0 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const number1 = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 })

export function eur(value: number): string {
  if (!Number.isFinite(value)) return '–'
  return Math.abs(value) >= 100 || Number.isInteger(value) ? euro0.format(value) : euro2.format(value)
}

export function pct(value: number, digits = 0): string {
  if (!Number.isFinite(value)) return '–'
  return `${(value * 100).toFixed(digits)}%`
}

export function energy(kwh: number): string {
  if (!Number.isFinite(kwh)) return '–'
  return Math.abs(kwh) >= 1000 ? `${number1.format(kwh / 1000)} MWh` : `${number0.format(kwh)} kWh`
}

export function power(kw: number): string {
  if (!Number.isFinite(kw)) return '–'
  return Math.abs(kw) >= 1000 ? `${number1.format(kw / 1000)} MW` : `${number0.format(kw)} kW`
}

/** Power in whole kW, never rounded to MW. Peak charges are billed per kW. */
export function kw(value: number): string {
  if (!Number.isFinite(value)) return '–'
  return `${number0.format(value)} kW`
}

export function mass(kg: number): string {
  if (!Number.isFinite(kg)) return '–'
  return Math.abs(kg) >= 1000 ? `${number1.format(kg / 1000)} t` : `${number0.format(kg)} kg`
}

export function num(value: number, digits = 0): string {
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: digits }).format(value)
}

function parts(iso: string, options: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat('en-GB', { timeZone: TZ, ...options }).format(new Date(iso))
}

export const time = (iso: string) => parts(iso, { hour: '2-digit', minute: '2-digit', hour12: false })
export const weekday = (iso: string) => parts(iso, { weekday: 'short' })
export const dayLabel = (iso: string) => parts(iso, { weekday: 'short', day: '2-digit', month: 'short' })
export const dateTime = (iso: string) =>
  parts(iso, { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })

export function relative(iso: string, now = Date.now()): string {
  const minutes = Math.round((now - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  return `${Math.round(hours / 24)} d ago`
}

export function localHour(iso: string): number {
  return Number(parts(iso, { hour: '2-digit', hour12: false })) % 24
}
