import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { get } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { NewRequestForm } from './NewRequestForm'
import type { QuotationRequest } from './types'

export default function QuotationsPage() {
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['quotation-requests', 'all'],
    queryFn: () => get<QuotationRequest[]>('/quotation-requests/'),
  })

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Quotations</h1>
          <p className="text-sm text-slate-500">Ask vendors for prices, compare them side by side and pick the winner.</p>
        </div>
        <Button onClick={() => setCreating(true)}>+ New request</Button>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && data.length === 0 && (
        <EmptyState
          title="No quotation requests yet"
          hint="Start one for a caterer, decorator or any other vendor type."
          action={<Button onClick={() => setCreating(true)}>+ New request</Button>}
        />
      )}
      {data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Wedding</Th>
              <Th>Looking for</Th>
              <Th>Guests</Th>
              <Th>Quotes by</Th>
              <Th>Received</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50">
                <Td>
                  <Link className="font-medium text-brand-700 hover:underline" to={`/quotations/${r.id}`}>
                    {r.wedding_title}
                  </Link>
                </Td>
                <Td>{r.category_name}</Td>
                <Td>{r.guest_count ?? '—'}</Td>
                <Td>{formatDate(r.due_date)}</Td>
                <Td>
                  {r.received_count} of {r.invited_count}
                </Td>
                <Td>
                  <Badge tone={r.status === 'OPEN' ? 'amber' : 'green'}>{r.status === 'OPEN' ? 'Open' : 'Closed'}</Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {creating && <NewRequestForm onClose={() => setCreating(false)} onCreated={(r) => navigate(`/quotations/${r.id}`)} />}
    </div>
  )
}
