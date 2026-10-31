import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { ApiError, get, post } from '@/api/client'
import { Badge, Button, Card, EmptyState, ErrorState, Input, Spinner } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import type { QuoteRequest } from './types'

export default function VendorRequestsPage() {
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['vendor-requests'], queryFn: () => get<QuoteRequest[]>('/portal/vendor/requests/') })
  if (isLoading) return <Spinner />
  if (error) return <ErrorState message={error.message} onRetry={refetch} />
  if (!data?.length) return <EmptyState title="No requests right now" hint="When we ask you for a price, the request shows up here." />
  return <div className="space-y-4">{data.map((r) => <RequestCard key={r.id} request={r} />)}</div>
}

function RequestCard({ request }: { request: QuoteRequest }) {
  const queryClient = useQueryClient()
  const mine = request.my_quotation
  const [editing, setEditing] = useState(!mine)
  const [total, setTotal] = useState(mine ? String(mine.total_paise / 100) : '')
  const [notes, setNotes] = useState(mine?.menu_notes ?? '')
  const send = useMutation({
    mutationFn: () => post(`/portal/vendor/requests/${request.id}/quote/`, { total_paise: Math.round(Number(total) * 100), menu_notes: notes }),
    onSuccess: () => {
      setEditing(false)
      queryClient.invalidateQueries({ queryKey: ['vendor-requests'] })
    },
  })
  const errors = send.error instanceof ApiError ? send.error.fields : {}
  const submit = (e: FormEvent) => {
    e.preventDefault()
    send.mutate()
  }
  const locked = mine?.status === 'SELECTED' || !request.open

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">{request.category} for {request.wedding}</h2>
          <p className="text-sm text-slate-500">
            {formatDate(request.date)} · {request.city}{request.guest_count ? ` · ${request.guest_count} guests` : ''}
            {request.reply_by && ` · reply by ${formatDate(request.reply_by)}`}
          </p>
        </div>
        {mine && <Badge tone={mine.status === 'SELECTED' ? 'green' : mine.status === 'REJECTED' ? 'red' : 'gray'}>{mine.status === 'SELECTED' ? 'You were selected' : mine.status === 'REJECTED' ? 'Not selected' : 'Quotation sent'}</Badge>}
      </div>
      {request.requirements && <p className="mt-3 whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{request.requirements}</p>}

      {mine && !editing && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
          <span>Your price: <b>{formatINR(mine.total_paise)}</b></span>
          {!locked && <Button variant="secondary" onClick={() => setEditing(true)}>Change my price</Button>}
        </div>
      )}
      {editing && !locked && (
        <form onSubmit={submit} className="mt-4 grid gap-3 sm:grid-cols-3">
          <Input label="Your total price (Rs)" type="number" min="0" value={total} onChange={(e) => setTotal(e.target.value)} error={errors.total_paise} required />
          <div className="sm:col-span-2">
            <Input label="What is included (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} error={errors.menu_notes} />
          </div>
          {send.error && !Object.keys(errors).length && <p className="text-sm text-red-600 sm:col-span-3">{send.error.message}</p>}
          <div className="sm:col-span-3"><Button type="submit" loading={send.isPending}>{mine ? 'Update price' : 'Send my price'}</Button></div>
        </form>
      )}
      {!request.open && !mine && <p className="mt-3 text-sm text-slate-500">This request is closed.</p>}
    </Card>
  )
}
