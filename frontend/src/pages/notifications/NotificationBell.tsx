import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { get, patch, post } from '@/api/client'
import { timeAgo } from '@/helpers/date'
import { SEVERITY_DOT, type NotificationList } from './types'

/** The bell in the top bar: unread count, the latest alerts, mark as read. Checks for new alerts every 30 seconds. */
export function NotificationBell() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const { data } = useQuery({
    queryKey: ['notifications', 'bell'],
    queryFn: () => get<NotificationList>('/notifications/', { limit: 8 }),
    refetchInterval: 30_000,
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['notifications'] })
  const markRead = useMutation({ mutationFn: (id: number) => patch(`/notifications/${id}/read/`), onSuccess: refresh })
  const markAll = useMutation({ mutationFn: () => post('/notifications/read-all/'), onSuccess: refresh })

  useEffect(() => {
    if (!open) return
    const close = (event: MouseEvent) => !box.current?.contains(event.target as Node) && setOpen(false)
    const escape = (event: KeyboardEvent) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', escape)
    }
  }, [open])

  const unread = data?.unread_count ?? 0
  return (
    <div ref={box} className="relative">
      <button
        aria-label={unread ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
        className="relative rounded-full p-2 text-slate-500 hover:bg-slate-100"
        onClick={() => setOpen((o) => !o)}
      >
        <Bell size={20} />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-brand-500 px-1 text-[10px] font-semibold text-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-96 max-w-[90vw] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <span className="text-sm font-semibold">Notifications</span>
            {unread > 0 && (
              <button className="text-xs font-medium text-brand-600 hover:underline" onClick={() => markAll.mutate()}>
                Mark all read
              </button>
            )}
          </div>
          <ul className="max-h-96 overflow-y-auto">
            {!data || data.results.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-slate-500">You are all caught up.</li>
            ) : (
              data.results.map((n) => (
                <li key={n.id}>
                  <button
                    className={`flex w-full gap-3 px-4 py-3 text-left text-sm hover:bg-slate-50 ${n.is_read ? 'text-slate-500' : ''}`}
                    onClick={() => !n.is_read && markRead.mutate(n.id)}
                  >
                    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.is_read ? 'bg-slate-200' : SEVERITY_DOT[n.severity]}`} />
                    <span className="min-w-0">
                      <span className={n.is_read ? '' : 'font-medium'}>{n.message}</span>
                      <span className="block text-xs text-slate-400">{timeAgo(n.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
          <Link to="/notifications" onClick={() => setOpen(false)} className="block border-t border-slate-100 px-4 py-2.5 text-center text-sm font-medium text-brand-600 hover:bg-slate-50">
            See all notifications
          </Link>
        </div>
      )}
    </div>
  )
}
