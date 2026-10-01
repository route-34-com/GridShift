import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export const SERIES = {
  price: 'var(--series-price)',
  solar: 'var(--series-solar)',
  wind: 'var(--series-wind)',
  battery: 'var(--series-battery)',
  grid: 'var(--series-grid)',
  demand: 'var(--series-demand)',
  baseline: 'var(--series-baseline)',
  brand: 'var(--brand)',
} as const

const MACHINE_COLORS = ['#0d9488', '#2563eb', '#c026d3', '#ea580c', '#4f46e5', '#0891b2', '#be123c', '#65a30d']

export function machineColor(index: number): string {
  return MACHINE_COLORS[index % MACHINE_COLORS.length]
}
