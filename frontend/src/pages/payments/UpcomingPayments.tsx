import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import { Badge, Card, CardTitle, EmptyState, ErrorState, Spinner } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import type { UpcomingPayment } from './types'

/** Vendor payments due soon, earliest first; late ones in red. Pass `items` to show one wedding's, or nothing for all. */
export function UpcomingPayments({ items, days = 14, showWedding = true }: { items?: UpcomingPayment[]; days?: number; showWedding?: boolean }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['upcoming-payments', days],
    queryFn: () => get<UpcomingPayment[]>('/finance/upcoming-payments/', { days }),
    enabled: !items,
  })
  const rows = items ?? data
  return (
    <Card>
      <CardTitle>Upcoming vendor payments</CardTitle>
      {!items && isLoading ? (
        <Spinner />
      ) : !rows ? (
        <ErrorState message={error?.message ?? 'Could not load payments'} onRetry={refetch} />
      ) : rows.length === 0 ? (
        <EmptyState title="Nothing due" hint="No vendor payments are due soon." />
      ) : (
        <ul className="divide-y divide-slate-100">
          {rows.map((row) => (
            <li key={`${row.kind}-${row.id}`} className="flex items-center justify-between gap-3 py-2.5 text-sm">
              <div className="min-w-0">
                <div className={`truncate font-medium ${row.overdue ? 'text-red-600' : ''}`}>{row.description}</div>
                <div className="truncate text-xs text-slate-500">
                  {showWedding && `${row.wedding_title} · `}
                  {row.overdue ? 'Overdue since ' : 'Due '}
                  {formatDate(row.due_date)}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {row.overdue && <Badge tone="red">Overdue</Badge>}
                <span className={`font-semibold tabular-nums ${row.overdue ? 'text-red-600' : ''}`}>
                  {formatINR(row.outstanding_paise)}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
