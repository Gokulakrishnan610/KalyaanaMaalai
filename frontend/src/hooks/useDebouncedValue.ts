import { useEffect, useState } from 'react'

/** The value, but only after it has stopped changing for `delay` ms. Use it for anything typed into a search box,
 *  so the server is asked once the person pauses, not on every keystroke. */
export function useDebouncedValue<T>(value: T, delay = 400): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}
