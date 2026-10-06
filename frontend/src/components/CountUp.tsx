import { useEffect, useRef, useState } from 'react'

const NUMBER = /-?\d[\d,]*(\.\d+)?/

/** Counts the number inside a formatted figure ("€54,973", "26,180 kW", "13%") up from zero when it first appears. */
export function CountUp({ text, duration = 900 }: { text: string; duration?: number }) {
  const match = NUMBER.exec(text)
  const target = match ? Number(match[0].replace(/,/g, '')) : null
  const [shown, setShown] = useState(text)
  const started = useRef(false)

  useEffect(() => {
    if (target === null || !match || started.current) {
      setShown(text)
      return
    }
    started.current = true
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return setShown(text)
    const decimals = match[1] ? match[1].length - 1 : 0
    const grouped = match[0].includes(',')
    const format = (v: number) =>
      text.replace(match[0], grouped ? v.toLocaleString('en-GB', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : v.toFixed(decimals))
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(p < 1 ? format(target * eased) : text)
      if (p < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
    // Only the first appearance animates; later changes show straight away.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text])

  return <>{shown}</>
}
