import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { get, patch, post } from '@/api/client'
import { Badge, Button, Card, CardTitle, ErrorState, Spinner } from '@/components/common'
import { formatDate, formatDateTime } from '@/helpers/date'
import { ComparisonTable } from './ComparisonTable'
import { QuotationForm } from './QuotationForm'
import type { Quotation, RequestDetail } from './types'

export default function RequestDetailPage() {
  const { id } = useParams()
  const requestId = Number(id)
  const queryClient = useQueryClient()
  const [form, setForm] = useState<{ vendorId?: number; quotation?: Quotation } | null>(null)
  const [sentNote, setSentNote] = useState('')

  const { data: request, isLoading, error, refetch } = useQuery({
    queryKey: ['quotation-request', requestId],
    queryFn: () => get<RequestDetail>(`/quotation-requests/${requestId}/`),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['quotation-request', requestId] })
    queryClient.invalidateQueries({ queryKey: ['quotation-requests'] })
  }
  const send = useMutation({
    mutationFn: () => post<{ sent_to: number }>(`/quotation-requests/${requestId}/send/`),
    onSuccess: (res) => {
      setSentNote(`Request sent to ${res.sent_to} vendor${res.sent_to === 1 ? '' : 's'}.`)
      refresh()
    },
  })
  const close = useMutation({
    mutationFn: (status: 'OPEN' | 'CLOSED') => patch(`/quotation-requests/${requestId}/`, { status }),
    onSuccess: refresh,
  })

  if (isLoading) return <Spinner />
  if (error || !request) return <ErrorState message={error?.message ?? 'Request not found'} onRetry={refetch} />

  const open = request.status === 'OPEN'
  const byId = new Map(request.quotations.map((q) => [q.id, q]))

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/quotations" className="text-sm text-brand-700 hover:underline">
            ← All requests
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold">
              {request.category_name} for {request.wedding_title}
            </h1>
            <Badge tone={open ? 'amber' : 'green'}>{open ? 'Open' : 'Closed'}</Badge>
          </div>
          <p className="text-sm text-slate-500">
            {request.guest_count ? `${request.guest_count} guests · ` : ''}
            quotes needed by {formatDate(request.due_date)}
            {request.sent_at && ` · sent ${formatDateTime(request.sent_at)}`}
          </p>
        </div>
        <div className="flex gap-2">
          {open && (
            <Button variant="secondary" loading={send.isPending} onClick={() => send.mutate()}>
              {request.sent_at ? 'Send again' : 'Send to vendors'}
            </Button>
          )}
          <Button variant="secondary" loading={close.isPending} onClick={() => close.mutate(open ? 'CLOSED' : 'OPEN')}>
            {open ? 'Close request' : 'Reopen'}
          </Button>
        </div>
      </div>
      {sentNote && <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{sentNote}</p>}
      {(send.error || close.error) && <ErrorState message={(send.error ?? close.error)!.message} />}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardTitle>What we asked for</CardTitle>
          <p className="whitespace-pre-line text-sm text-slate-600">{request.requirements || 'No special requirements written down.'}</p>
        </Card>
        <Card className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <CardTitle className="mb-0">
              Invited vendors · {request.received_count} of {request.invited_count} replied
            </CardTitle>
          </div>
          {request.invited_vendors.length === 0 ? (
            <p className="text-sm text-slate-500">No vendors invited yet.</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {request.invited_vendors.map((v) => {
                const quote = v.quotation_id ? byId.get(v.quotation_id) : undefined
                return (
                  <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <div>
                      <Link to={`/vendors/${v.id}`} className="font-medium text-brand-700 hover:underline">
                        {v.name}
                      </Link>
                      <div className="text-xs text-slate-500">
                        {v.phone}
                        {v.email && ` · ${v.email}`}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {v.received ? <Badge tone="green">Received</Badge> : <Badge tone="amber">Waiting</Badge>}
                      {open && quote?.status !== 'SELECTED' && (
                        <Button variant="secondary" onClick={() => setForm({ vendorId: v.id, quotation: quote })}>
                          {v.received ? 'Edit quotation' : 'Add quotation'}
                        </Button>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Compare quotations</h2>
          {open && <Button onClick={() => setForm({})}>+ Add quotation</Button>}
        </div>
        <ComparisonTable requestId={requestId} />
      </section>

      {form && (
        <QuotationForm request={request} vendorId={form.vendorId} quotation={form.quotation} onClose={() => setForm(null)} />
      )}
    </div>
  )
}
