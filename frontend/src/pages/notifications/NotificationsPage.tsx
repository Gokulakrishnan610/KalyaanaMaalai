import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { get, patch, post } from '@/api/client'
import { Badge, Button, Card, EmptyState, ErrorState, PageHeader, Spinner, cn } from '@/components/common'
import { formatDateTime } from '@/helpers/date'
import { SEVERITY_DOT, type NotificationList } from './types'

const TONE = { info: 'blue', warning: 'amber', critical: 'red' } as const

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<'unread' | 'all'>('unread')
  const [limit, setLimit] = useState(15)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['notifications', 'all'],
    queryFn: () => get<NotificationList>('/notifications/', { limit: 100 }),
    refetchInterval: 30_000,
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['notifications'] })
  const markRead = useMutation({ mutationFn: (id: number) => patch(`/notifications/${id}/read/`), onSuccess: refresh })
  const markAll = useMutation({ mutationFn: () => post('/notifications/read-all/'), onSuccess: refresh })

  if (isLoading) return <Spinner />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load notifications'} onRetry={refetch} />
  const list = filter === 'unread' ? data.results.filter((n) => !n.is_read) : data.results
  return (
    <div>
      <PageHeader
        title="Notifications"
        description={data.unread_count ? `${data.unread_count} unread` : 'You are all caught up.'}
        actions={data.unread_count > 0 && (
          <Button variant="secondary" loading={markAll.isPending} onClick={() => markAll.mutate()}>
            Mark all read
          </Button>
        )}
      />
      <div className="mb-4 inline-flex rounded-lg border border-slate-200 bg-white p-0.5 text-sm">
        {(['unread', 'all'] as const).map((f) => (
          <button key={f} onClick={() => { setFilter(f); setLimit(15) }} className={cn('rounded-md px-3 py-1.5 capitalize', filter === f ? 'bg-slate-900 text-white' : 'text-slate-600 hover:text-slate-900')}>
            {f}
          </button>
        ))}
      </div>
      {list.length === 0 ? (
        <EmptyState title={filter === 'unread' ? 'Nothing unread' : 'No notifications yet'} hint="Late vendors and payments that are due will show up here." />
      ) : (
        <Card className="divide-y divide-slate-100 p-0">
          {list.slice(0, limit).map((n) => (
            <div key={n.id} className="flex items-start gap-3 px-5 py-3.5">
              <span className={`mt-2 h-2 w-2 shrink-0 rounded-full ${n.is_read ? 'bg-slate-200' : SEVERITY_DOT[n.severity]}`} />
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${n.is_read ? 'text-slate-500' : 'font-medium'}`}>{n.message}</p>
                <p className="text-xs text-slate-400">{formatDateTime(n.created_at)}</p>
              </div>
              <Badge tone={TONE[n.severity]}>{n.severity}</Badge>
              {!n.is_read && (
                <Button variant="ghost" size="sm" onClick={() => markRead.mutate(n.id)}>
                  Mark read
                </Button>
              )}
            </div>
          ))}
          {list.length > limit && (
            <button onClick={() => setLimit((l) => l + 15)} className="w-full py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900">
              Show {Math.min(15, list.length - limit)} more of {list.length - limit}
            </button>
          )}
        </Card>
      )}
    </div>
  )
}
