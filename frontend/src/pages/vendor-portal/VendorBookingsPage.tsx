import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MapPin, Users } from 'lucide-react'
import { get, post } from '@/api/client'
import { Badge, Button, Card, EmptyState, ErrorState, Spinner } from '@/components/common'
import { formatDate, formatDateTime } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import type { Booking } from './types'

const arrivalTone = { PENDING: 'gray', ON_TIME: 'green', LATE: 'red', GRACE: 'amber' } as const

export default function VendorBookingsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['vendor-bookings'], queryFn: () => get<Booking[]>('/portal/vendor/bookings/') })
  // "I have arrived" uses the same public check-in the staff site already had
  const arrive = useMutation({
    mutationFn: (code: string) => post(`/public/checkin/${code}/arrive/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['vendor-bookings'] }),
  })

  if (isLoading) return <Spinner />
  if (error) return <ErrorState message={error.message} onRetry={refetch} />
  if (!data?.length) return <EmptyState title="No bookings yet" hint="When we pick you for a wedding, it shows up here with the schedule." />

  return (
    <div className="space-y-4">
      {data.map((b) => (
        <Card key={`${b.wedding}-${b.start_date}`}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="text-lg font-semibold">{b.wedding}</h2>
              <div className="mt-1 flex flex-wrap items-center gap-4 text-sm text-slate-500">
                <span>{formatDate(b.start_date)}{b.end_date !== b.start_date && ` to ${formatDate(b.end_date)}`}</span>
                <span className="flex items-center gap-1"><MapPin size={14} />{b.city}</span>
                <span className="flex items-center gap-1"><Users size={14} />{b.guest_count} guests</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-slate-500">Agreed amount</div>
              <div className="text-lg font-semibold">{formatINR(b.agreed_amount_paise)}</div>
            </div>
          </div>

          {b.arrivals.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="text-sm font-medium text-slate-700">Arrival</div>
              {b.arrivals.map((a) => (
                <div key={a.code} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span>{a.function ?? 'Event'}: expected {formatDateTime(a.expected_at)}</span>
                  {a.arrived_at ? (
                    <Badge tone={arrivalTone[a.status as keyof typeof arrivalTone] ?? 'green'}>Arrived {formatDateTime(a.arrived_at)}</Badge>
                  ) : (
                    <Button loading={arrive.isPending} onClick={() => arrive.mutate(a.code)}>I have arrived</Button>
                  )}
                </div>
              ))}
            </div>
          )}

          {b.schedule.length > 0 && (
            <div className="mt-4">
              <div className="mb-1 text-sm font-medium text-slate-700">Your schedule</div>
              <ul className="divide-y divide-slate-100 text-sm">
                {b.schedule.map((s, i) => (
                  <li key={i} className="flex flex-wrap justify-between gap-2 py-2">
                    <span>{s.title} <span className="text-slate-400">({s.function})</span>{s.notes && <span className="block text-xs text-slate-500">{s.notes}</span>}</span>
                    <span className="text-slate-500">{formatDateTime(s.starts_at)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      ))}
    </div>
  )
}
