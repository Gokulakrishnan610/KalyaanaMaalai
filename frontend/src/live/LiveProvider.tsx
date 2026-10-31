import { useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useToast } from '@/components/common'
import { TOKEN_KEY } from '@/api/client'
import { useLogin } from '@/login/LoginContext'
import { NotLoggedInError, readStream, type LiveEvent } from './stream'

export type LiveStatus = 'connecting' | 'live' | 'offline'

const StatusContext = createContext<LiveStatus>('connecting')

// eslint-disable-next-line react-refresh/only-export-components
export const useLiveStatus = () => useContext(StatusContext)

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

/** Which screens to refresh when each kind of event arrives (the first word of a query key). */
const REFRESH: Record<string, string[]> = {
  'task.updated': ['tasks', 'wedding-progress', 'wedding', 'weddings', 'dashboard'],
  'vendor.arrival': ['checkins', 'wedding', 'vendor-profile', 'dashboard'],
  'schedule.updated': ['schedule', 'wedding-schedule', 'wedding'],
  'quotation.received': ['quotation-requests', 'quotation-request', 'comparison', 'dashboard'],
  'quotation.updated': ['quotation-requests', 'quotation-request', 'comparison'],
  'payment.recorded': ['finance', 'finance-overview', 'upcoming-payments', 'payment-summary', 'clients', 'dashboard'],
  'finance.updated': ['finance', 'finance-overview', 'upcoming-payments', 'payment-summary', 'dashboard'],
  'notification.new': ['notifications', 'dashboard'],
  'incident.updated': ['incidents', 'dashboard'],
  'enquiry.updated': ['enquiries', 'clients', 'dashboard'],
}

/**
 * Keeps one live connection open while someone is logged in. Each event refreshes the screens it affects and,
 * for alerts, shows a pop-up. If the connection drops it reconnects by itself and catches up on what it missed.
 */
export function LiveProvider({ children }: { children: ReactNode }) {
  const { user } = useLogin()
  const queryClient = useQueryClient()
  const { show } = useToast()
  const [status, setStatus] = useState<LiveStatus>('connecting')
  const showRef = useRef(show)
  showRef.current = show

  const userId = user?.id
  useEffect(() => {
    if (!userId) return
    const abort = new AbortController()
    let lastId = 0
    const pending = new Set<string>()
    let timer: number | undefined

    // several events in a row (a task moving also refreshes the dashboard) cause one refresh, not many
    const refreshSoon = (keys: string[]) => {
      keys.forEach((k) => pending.add(k))
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        pending.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }))
        pending.clear()
      }, 250)
    }

    const onEvent = (event: LiveEvent) => {
      lastId = Math.max(lastId, event.id)
      refreshSoon(REFRESH[event.type] ?? [])
      if (event.type === 'notification.new') {
        const severity = event.data.severity as string
        const tone = severity === 'critical' ? 'critical' : severity === 'warning' ? 'warning' : 'info'
        showRef.current(String(event.data.message), tone)
      }
    }

    void (async () => {
      let wait = 1000
      while (!abort.signal.aborted) {
        const token = localStorage.getItem(TOKEN_KEY)
        if (!token) return
        try {
          setStatus('connecting')
          await readStream(`${API}/live/stream/`, token, lastId, {
            onOpen: () => {
              setStatus('live')
              wait = 1000
              refreshSoon(Object.values(REFRESH).flat()) // after (re)connecting, make sure nothing on screen is stale
            },
            onEvent,
          }, abort.signal)
        } catch (error) {
          if (abort.signal.aborted || error instanceof NotLoggedInError) return
        }
        if (abort.signal.aborted) return
        setStatus('offline')
        await new Promise((resolve) => window.setTimeout(resolve, wait))
        wait = Math.min(wait * 2, 10000)
      }
    })()

    return () => {
      abort.abort()
      window.clearTimeout(timer)
    }
  }, [userId, queryClient])

  return <StatusContext.Provider value={status}>{children}</StatusContext.Provider>
}
