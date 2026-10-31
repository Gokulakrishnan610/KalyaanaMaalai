import { useQuery } from '@tanstack/react-query'
import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, Spinner, Table, Td, Th } from '@/components/common'
import { get, type Page } from '@/api/client'
import { formatDate } from '@/helpers/date'

export interface Client {
  id: number
  couple_name: string
  bride_name: string
  groom_name: string
  phone: string
  email: string
  city: string
  created_at: string
}

export default function ClientsPage() {
  const [search, setSearch] = useState('')
  const deferred = useDeferredValue(search)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['clients', deferred],
    queryFn: () => get<Page<Client>>('/clients/', { q: deferred || undefined, page_size: 100 }),
  })

  return (
    <div>
      <h1 className="text-2xl font-semibold">Clients</h1>
      <p className="mb-5 text-sm text-slate-500">Couples who have booked with us. New clients appear when an enquiry is converted.</p>

      <input
        aria-label="Search clients"
        placeholder="Search name, phone or city"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 w-72 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
      />

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && data.results.length === 0 && (
        <EmptyState title="No clients yet" hint="Convert an enquiry to create the first client." />
      )}
      {data && data.results.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Couple</Th>
              <Th>Phone</Th>
              <Th>City</Th>
              <Th>Client since</Th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <Td>
                  <Link className="font-medium text-brand-700 hover:underline" to={`/clients/${c.id}`}>
                    {c.couple_name}
                  </Link>
                </Td>
                <Td>{c.phone}</Td>
                <Td>{c.city || '-'}</Td>
                <Td>{formatDate(c.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  )
}
