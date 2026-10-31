import { useMutation, useQuery } from '@tanstack/react-query'
import { Undo2 } from 'lucide-react'
import { useState } from 'react'
import { get, remove, type Page } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDateTime } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { useRefreshMoney } from './finance'
import { methodLabel, type LedgerRow } from './types'

const SOURCE = {
  LINK: { label: 'Payment link', tone: 'blue' },
  ONLINE: { label: 'Online', tone: 'blue' },
  MANUAL: { label: 'Entered by hand', tone: 'gray' },
} as const

/** Every payment that has happened, newest first: proof of what was paid, how, and who recorded it. A mistaken entry can be undone. */
export function PaymentHistory({ weddingId }: { weddingId: number | null }) {
  const canEdit = useLogin().hasRole('PLANNER')
  const refresh = useRefreshMoney()
  const [direction, setDirection] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finance', 'ledger', weddingId ?? 'all', direction, page],
    queryFn: () => get<Page<LedgerRow>>('/payments/', { wedding: weddingId ?? undefined, direction: direction || undefined, page, page_size: 25 }),
  })
  const undo = useMutation({ mutationFn: (id: number) => remove(`/payments/${id}/`), onSuccess: () => refresh() })

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-slate-500">
          Every payment, in and out. If you typed one in by mistake, undo it here (the founder is told). Online payments cannot be undone here: refund those in Razorpay.
        </p>
        <div className="w-44">
          <Select
            aria-label="Show"
            value={direction}
            onChange={(e) => {
              setDirection(e.target.value)
              setPage(1)
            }}
          >
            <option value="">Money in and out</option>
            <option value="IN">Received from customers</option>
            <option value="OUT">Paid to vendors</option>
          </Select>
        </div>
      </div>

      {isLoading ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorState message={error?.message ?? 'Could not load payments'} onRetry={refetch} />
      ) : data.results.length === 0 ? (
        <EmptyState title="No payments yet" hint="Payments appear here as soon as they are recorded." />
      ) : (
        <>
          <Table>
            <thead>
              <tr>
                <Th>Date</Th>
                <Th>Who</Th>
                <Th>How</Th>
                <Th>Recorded</Th>
                <Th className="text-right">Amount</Th>
                {canEdit && <Th />}
              </tr>
            </thead>
            <tbody>
              {data.results.map((p) => (
                <tr key={p.id}>
                  <Td className="whitespace-nowrap">{formatDateTime(p.paid_at)}</Td>
                  <Td>
                    <div className="font-medium">{p.party}</div>
                    <div className="text-xs text-slate-500">
                      {p.what}
                      {weddingId === null && ` · ${p.wedding_title}`}
                    </div>
                  </Td>
                  <Td>
                    <div>{methodLabel(p.method)}</div>
                    {p.reference && <div className="max-w-[10rem] truncate text-xs text-slate-500">{p.reference}</div>}
                  </Td>
                  <Td>
                    <Badge tone={SOURCE[p.source].tone}>{SOURCE[p.source].label}</Badge>
                    {p.recorded_by_name && <div className="mt-0.5 text-xs text-slate-500">by {p.recorded_by_name}</div>}
                  </Td>
                  <Td className={`text-right font-semibold tabular-nums ${p.direction === 'IN' ? 'text-emerald-600' : 'text-slate-700'}`}>
                    {p.direction === 'IN' ? '+' : '−'}
                    {formatINR(p.amount_paise)}
                  </Td>
                  {canEdit && (
                    <Td className="text-right">
                      {p.can_undo && (
                        <Button
                          variant="ghost"
                          title="Undo this payment"
                          aria-label={`Undo payment of ${formatINR(p.amount_paise)} from ${p.party}`}
                          onClick={() => window.confirm('Undo this payment? Use this only if it was entered by mistake.') && undo.mutate(p.id)}
                        >
                          <Undo2 size={14} />
                        </Button>
                      )}
                    </Td>
                  )}
                </tr>
              ))}
            </tbody>
          </Table>
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>{data.count} payments</span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={!data.previous} onClick={() => setPage((n) => n - 1)}>
                Previous
              </Button>
              <Button variant="secondary" disabled={!data.next} onClick={() => setPage((n) => n + 1)}>
                Next
              </Button>
            </div>
          </div>
        </>
      )}
      {undo.error && <p className="text-sm text-red-600">{undo.error.message}</p>}
    </section>
  )
}
