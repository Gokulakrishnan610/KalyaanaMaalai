import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { get, patch, post } from '@/api/client'
import { Badge, Button, Card, EmptyState, ErrorState, Spinner } from '@/components/common'
import { formatDateTime } from '@/helpers/date'
import { SEVERITY_DOT, type NotificationList } from './types'

const TONE = { info: 'blue', warning: 'amber', critical: 'red' } as const

export default function NotificationsPage() {
  const queryClient = useQueryClient()
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
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Notifications</h1>
          <p className="text-sm text-slate-500">{data.unread_count ? `${data.unread_count} unread` : 'You are all caught up.'}</p>
        </div>
        {data.unread_count > 0 && (
          <Button variant="secondary" loading={markAll.isPending} onClick={() => markAll.mutate()}>
            Mark all read
          </Button>
        )}
      </div>
      {data.results.length === 0 ? (
        <EmptyState title="No notifications yet" hint="Late vendors and payments that are due will show up here." />
      ) : (
        <Card className="divide-y divide-slate-100 p-0">
          {data.results.map((n) => (
            <div key={n.id} className="flex items-start gap-3 px-5 py-3.5">
              <span className={`mt-2 h-2 w-2 shrink-0 rounded-full ${n.is_read ? 'bg-slate-200' : SEVERITY_DOT[n.severity]}`} />
              <div className="min-w-0 flex-1">
                <p className={`text-sm ${n.is_read ? 'text-slate-500' : 'font-medium'}`}>{n.message}</p>
                <p className="text-xs text-slate-400">{formatDateTime(n.created_at)}</p>
              </div>
              <Badge tone={TONE[n.severity]}>{n.severity}</Badge>
              {!n.is_read && (
                <Button variant="ghost" onClick={() => markRead.mutate(n.id)}>
                  Mark read
                </Button>
              )}
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}
