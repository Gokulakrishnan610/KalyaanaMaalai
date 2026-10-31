import { useEffect, useRef, useState } from 'react'

/** A number that counts up from zero when it appears. */
export function CountUp({ value, format = (n: number) => String(Math.round(n)), ms = 900 }: { value: number; format?: (n: number) => string; ms?: number }) {
  const [shown, setShown] = useState(0)
  const frame = useRef(0)

  useEffect(() => {
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      setShown(value * (1 - Math.pow(1 - t, 3))) // ease out
      if (t < 1) frame.current = requestAnimationFrame(tick)
    }
    frame.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame.current)
  }, [value, ms])

  return <>{format(shown)}</>
}
