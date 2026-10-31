import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get } from '@/api/client'
import { Badge, Button, Card, CardTitle, EmptyState, ErrorState, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { NewRequestForm } from '@/pages/quotations/NewRequestForm'
import type { QuotationRequest } from '@/pages/quotations/types'
import { RateVendorModal } from './RateVendorModal'
import type { WeddingVendor } from './types'

/** The "Vendors" tab of a wedding: who we picked, and the quotation requests still in progress. */
export function VendorsTab({ weddingId }: { weddingId: number }) {
  const [creating, setCreating] = useState(false)
  const [rating, setRating] = useState<WeddingVendor | null>(null)

  const vendors = useQuery({
    queryKey: ['wedding-vendors', weddingId],
    queryFn: () => get<WeddingVendor[]>(`/weddings/${weddingId}/vendors/`),
  })
  const requests = useQuery({
    queryKey: ['quotation-requests', 'wedding', weddingId],
    queryFn: () => get<QuotationRequest[]>(`/weddings/${weddingId}/quotation-requests/`),
  })

  return (
    <div className="space-y-6">
      <section>
        <CardTitle className="text-base">Selected vendors</CardTitle>
        {vendors.isLoading && <Spinner />}
        {vendors.error && <ErrorState message={vendors.error.message} onRetry={vendors.refetch} />}
        {vendors.data?.length === 0 && (
          <EmptyState title="No vendors selected yet" hint="Request quotations below, compare them, and pick a winner." />
        )}
        {vendors.data && vendors.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Category</Th>
                <Th>Vendor</Th>
                <Th className="text-right">Agreed amount</Th>
                <Th>Status</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {vendors.data.map((v) => (
                <tr key={v.id}>
                  <Td>{v.category}</Td>
                  <Td>
                    <Link className="font-medium text-brand-700 hover:underline" to={`/vendors/${v.vendor.id}`}>
                      {v.vendor.name}
                    </Link>
                  </Td>
                  <Td className="text-right">{formatINR(v.agreed_amount_paise)}</Td>
                  <Td>
                    <Badge tone="green">{v.status.toLowerCase()}</Badge>
                  </Td>
                  <Td className="text-right">
                    <Button variant="ghost" onClick={() => setRating(v)}>
                      Rate
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <CardTitle className="mb-0 text-base">Quotation requests</CardTitle>
          <Button onClick={() => setCreating(true)}>+ New request</Button>
        </div>
        {requests.isLoading && <Spinner />}
        {requests.error && <ErrorState message={requests.error.message} onRetry={requests.refetch} />}
        {requests.data?.length === 0 && <EmptyState title="No requests yet" hint="For example: ask three caterers for a price." />}
        <div className="grid gap-3">
          {requests.data?.map((r) => (
            <Link key={r.id} to={`/quotations/${r.id}`} className="block">
              <Card lift className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium">{r.category_name}</div>
                  <div className="text-sm text-slate-500">
                    {r.guest_count ? `${r.guest_count} guests · ` : ''}quotes by {formatDate(r.due_date)}
                  </div>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-slate-600">
                    {r.received_count} of {r.invited_count} received
                  </span>
                  <Badge tone={r.status === 'OPEN' ? 'amber' : 'green'}>{r.status === 'OPEN' ? 'Open' : 'Closed'}</Badge>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {creating && <NewRequestForm weddingId={weddingId} onClose={() => setCreating(false)} />}
      {rating && (
        <RateVendorModal vendorId={rating.vendor.id} vendorName={rating.vendor.name} weddingId={weddingId} onClose={() => setRating(null)} />
      )}
    </div>
  )
}

export default VendorsTab
