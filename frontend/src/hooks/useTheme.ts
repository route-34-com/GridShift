import { useCallback, useState } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'gridshift-theme'

function current(): Theme {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light'
}

function remember(theme: Theme): void {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    return
  }
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(current)
  const toggle = useCallback(() => {
    const next: Theme = current() === 'dark' ? 'light' : 'dark'
    document.documentElement.classList.toggle('dark', next === 'dark')
    remember(next)
    setTheme(next)
  }, [])
  return [theme, toggle]
}
