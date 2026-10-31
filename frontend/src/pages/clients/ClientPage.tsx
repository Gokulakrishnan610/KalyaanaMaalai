import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Badge, Card, CardTitle, EmptyState, ErrorState, Spinner } from '@/components/common'
import { get } from '@/api/client'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { sourceInfo, statusInfo, type Source, type Status } from '@/pages/enquiries/types'
import type { Client } from './ClientsPage'

interface ClientProfile extends Client {
  enquiries: { id: number; source: Source; status: Status; created_at: string }[]
  weddings: { id: number; title: string; start_date: string; city: string; guest_count: number; status: string }[]
  invoiced_paise: number
  paid_paise: number
  outstanding_paise: number
}

export default function ClientPage() {
  const { id } = useParams()
  const { data: client, isLoading, error, refetch } = useQuery({
    queryKey: ['clients', 'profile', id],
    queryFn: () => get<ClientProfile>(`/clients/${id}/`),
  })

  if (isLoading) return <Spinner />
  if (error || !client) return <ErrorState message={error?.message ?? 'Client not found'} onRetry={refetch} />

  return (
    <div className="space-y-5">
      <div>
        <Link to="/clients" className="text-sm text-brand-700 hover:underline">
          ← All clients
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">{client.couple_name}</h1>
        <p className="text-sm text-slate-500">
          {client.phone}
          {client.email && ` · ${client.email}`}
          {client.city && ` · ${client.city}`}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ['Invoiced', client.invoiced_paise],
          ['Paid', client.paid_paise],
          ['Still owes', client.outstanding_paise],
        ].map(([label, value]) => (
          <Card key={label as string}>
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-1 text-2xl font-semibold">{formatINR(value as number)}</div>
          </Card>
        ))}
      </div>

      <Card>
        <CardTitle>Weddings</CardTitle>
        {client.weddings.length === 0 ? (
          <EmptyState title="No wedding project yet" hint="Start one when converting the enquiry." />
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {client.weddings.map((w) => (
              <li key={w.id} className="flex items-center justify-between py-2">
                <span className="font-medium">{w.title}</span>
                <span className="text-slate-500">
                  {formatDate(w.start_date)} · {w.city} · {w.guest_count} guests
                </span>
                <Badge tone={w.status === 'COMPLETED' ? 'green' : w.status === 'CANCELLED' ? 'red' : 'blue'}>{w.status.charAt(0) + w.status.slice(1).toLowerCase()}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardTitle>Enquiry history</CardTitle>
        {client.enquiries.length === 0 ? (
          <p className="text-sm text-slate-500">No linked enquiries.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {client.enquiries.map((e) => (
              <li key={e.id} className="flex items-center justify-between py-2">
                <span>
                  {sourceInfo(e.source).label}
                </span>
                <span className="text-slate-500">{formatDate(e.created_at)}</span>
                <Badge tone={statusInfo(e.status).tone}>{statusInfo(e.status).label}</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
