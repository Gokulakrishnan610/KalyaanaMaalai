import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import { Badge, Card, CardTitle, EmptyState, ErrorState, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import type { VendorPayments } from './types'

const tone = { PAID: 'green', PARTIAL: 'amber', UNPAID: 'gray' } as const

export default function VendorPaymentsPage() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['vendor-payments'], queryFn: () => get<VendorPayments>('/portal/vendor/payments/') })
  if (isLoading) return <Spinner />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load'} onRetry={refetch} />
  const due = data.bills.reduce((sum, b) => sum + b.remaining_paise, 0)

  return (
    <div className="space-y-5">
      <Card>
        <div className="text-sm text-slate-500">Still to be paid to you</div>
        <div className="text-2xl font-semibold">{formatINR(due)}</div>
      </Card>
      {data.bills.length === 0 ? (
        <EmptyState title="No bills yet" hint="Your bills appear here once you are booked for a wedding." />
      ) : (
        <Table>
          <thead><tr><Th>Wedding</Th><Th>For</Th><Th>Amount</Th><Th>Paid</Th><Th>Due date</Th><Th>Status</Th></tr></thead>
          <tbody>
            {data.bills.map((b) => (
              <tr key={b.id}>
                <Td>{b.wedding}</Td><Td>{b.description}</Td><Td>{formatINR(b.amount_paise)}</Td><Td>{formatINR(b.paid_paise)}</Td>
                <Td>{b.due_date ? formatDate(b.due_date) : '-'}</Td>
                <Td><Badge tone={tone[b.status as keyof typeof tone] ?? 'gray'}>{b.status}</Badge></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      {data.payments.length > 0 && (
        <Card>
          <CardTitle>Payments we have made to you</CardTitle>
          <ul className="divide-y divide-slate-100 text-sm">
            {data.payments.map((p, i) => (
              <li key={i} className="flex flex-wrap justify-between gap-2 py-2">
                <span>{p.wedding} <span className="text-slate-400">via {p.method}{p.reference && `, ref ${p.reference}`}</span></span>
                <span><b>{formatINR(p.amount_paise)}</b> <span className="text-slate-500">{formatDate(p.paid_at)}</span></span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
