import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { get, remove } from '@/api/client'
import { Badge, Button, Card, CardTitle, CountUp, EmptyState, ErrorState, Spinner, cn } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { RateVendorModal } from './RateVendorModal'
import { Stars } from './Stars'
import type { Performance, VendorProfile } from './types'
import { VendorForm } from './VendorForm'

const TABS = ['Overview', 'Weddings', 'Quotations', 'Performance'] as const
type Tab = (typeof TABS)[number]

const quoteTone = { RECEIVED: 'gray', SELECTED: 'green', REJECTED: 'red' } as const

export default function VendorProfilePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('Overview')
  const [editing, setEditing] = useState(false)
  const [rating, setRating] = useState<number | null>(null)

  const { data: vendor, isLoading, error, refetch } = useQuery({
    queryKey: ['vendor-profile', id],
    queryFn: () => get<VendorProfile>(`/vendors/${id}/`),
  })

  const del = useMutation({
    mutationFn: () => remove(`/vendors/${id}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] })
      navigate('/vendors')
    },
  })

  if (isLoading) return <Spinner />
  if (error || !vendor) return <ErrorState message={error?.message ?? 'Vendor not found'} onRetry={refetch} />

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/vendors" className="text-sm text-brand-700 hover:underline">
            ← All vendors
          </Link>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold">{vendor.name}</h1>
            <Badge tone="brand">{vendor.category_name}</Badge>
          </div>
          <div className="mt-1">
            <Stars value={vendor.avg_rating} />
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setEditing(true)}>
            Edit
          </Button>
          <Button
            variant="danger"
            loading={del.isPending}
            onClick={() => window.confirm(`Delete ${vendor.name}? This cannot be undone.`) && del.mutate()}
          >
            Delete
          </Button>
        </div>
      </div>
      {del.error && <ErrorState message={del.error.message} />}

      <div role="tablist" className="flex gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={cn(
              '-mb-px border-b-2 px-4 py-2 text-sm font-medium',
              tab === t ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && <Overview vendor={vendor} />}
      {tab === 'Weddings' && <WeddingsList vendor={vendor} onRate={setRating} />}
      {tab === 'Quotations' && <QuotationsList vendor={vendor} />}
      {tab === 'Performance' && <Scorecard performance={vendor.performance} />}

      {editing && (
        <VendorForm
          open
          vendor={vendor}
          onClose={() => setEditing(false)}
          onSaved={() => queryClient.invalidateQueries({ queryKey: ['vendor-profile', id] })}
        />
      )}
      {rating !== null && (
        <RateVendorModal
          vendorId={vendor.id}
          vendorName={vendor.name}
          weddingId={rating}
          existing={vendor.ratings.find((r) => r.wedding_id === rating)} onClose={() => setRating(null)} />
      )}
    </div>
  )
}

function Overview({ vendor }: { vendor: VendorProfile }) {
  const facts: [string, string][] = [
    ['Contact person', vendor.contact_person || '—'],
    ['Phone', vendor.phone],
    ['Email', vendor.email || '—'],
    ['City', vendor.city || '—'],
  ]
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardTitle>Contact</CardTitle>
        <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          {facts.map(([label, value]) => (
            <div key={label}>
              <dt className="text-slate-500">{label}</dt>
              <dd className="font-medium">{value}</dd>
            </div>
          ))}
        </dl>
        {vendor.notes && <p className="mt-4 whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-600">{vendor.notes}</p>}
      </Card>
      <div className="grid gap-4">
        <Card>
          <div className="text-sm text-slate-500">Weddings with us</div>
          <div className="mt-1 text-2xl font-semibold">
            <CountUp value={vendor.weddings_count} />
          </div>
        </Card>
        <Card>
          <div className="text-sm text-slate-500">Total paid to them</div>
          <div className="mt-1 text-2xl font-semibold">
            <CountUp value={vendor.total_paid_paise} format={formatINR} />
          </div>
        </Card>
      </div>
    </div>
  )
}

function WeddingsList({ vendor, onRate }: { vendor: VendorProfile; onRate: (weddingId: number) => void }) {
  if (vendor.weddings.length === 0) {
    return <EmptyState title="Not booked on any wedding yet" hint="They appear here once you select their quotation for a wedding." />
  }
  const ratings = new Map(vendor.ratings.map((r) => [r.wedding_id, r]))
  return (
    <Card className="divide-y divide-slate-100 p-0">
      {vendor.weddings.map((w) => {
        const rated = ratings.get(w.id)
        return (
          <div key={w.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm">
            <div>
              <div className="font-medium">{w.title}</div>
              <div className="text-slate-500">
                {formatDate(w.start_date)} · agreed {formatINR(w.agreed_amount_paise)}
              </div>
              {rated?.comment && <div className="mt-1 text-slate-600">“{rated.comment}”</div>}
            </div>
            <div className="flex items-center gap-3">
              <Badge tone={w.status === 'COMPLETED' ? 'green' : 'blue'}>{w.status.toLowerCase()}</Badge>
              {rated ? (
                <Stars value={(rated.punctuality + rated.quality + rated.pricing) / 3} />
              ) : null}
              <Button variant="secondary" onClick={() => onRate(w.id)}>
                {rated ? 'Update rating' : 'Rate'}
              </Button>
            </div>
          </div>
        )
      })}
    </Card>
  )
}

function QuotationsList({ vendor }: { vendor: VendorProfile }) {
  if (vendor.quotations.length === 0) return <EmptyState title="No quotations from this vendor yet" />
  return (
    <Card className="divide-y divide-slate-100 p-0">
      {vendor.quotations.map((q) => (
        <Link key={q.id} to={`/quotations/${q.request_id}`} className="flex items-center justify-between gap-3 px-5 py-3 text-sm hover:bg-slate-50">
          <div>
            <div className="font-medium">{q.wedding_title}</div>
            <div className="text-slate-500">
              {formatDate(q.created_at)}
              {q.price_per_plate_paise ? ` · ${formatINR(q.price_per_plate_paise)} per plate` : ''}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-semibold">{formatINR(q.total_paise)}</span>
            <Badge tone={quoteTone[q.status]}>{q.status.toLowerCase()}</Badge>
          </div>
        </Link>
      ))}
    </Card>
  )
}

function Bar({ label, value, max, text, hint }: { label: string; value: number | null; max: number; text: string; hint?: string }) {
  const percent = value == null ? 0 : Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="text-slate-600">{value == null ? 'No data yet' : text}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100" role="meter" aria-label={label} aria-valuenow={value ?? 0} aria-valuemax={max}>
        <div className="bar-grow h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500" style={{ width: `${percent}%` }} />
      </div>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

function Scorecard({ performance: p }: { performance: Performance }) {
  if (p.ratings_count === 0 && p.arrivals_counted === 0) {
    return <EmptyState title="No scorecard yet" hint="Rate this vendor after a wedding, and wedding-day check-ins will fill in punctuality." />
  }
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="flex flex-col items-center justify-center text-center">
        <div className="text-sm text-slate-500">Overall score</div>
        <div className="mt-1 text-5xl font-semibold text-brand-700">{p.score == null ? '—' : <CountUp value={p.score} />}</div>
        <div className="text-xs text-slate-500">out of 100 · from {p.ratings_count} rating{p.ratings_count === 1 ? '' : 's'}</div>
      </Card>
      <Card className="space-y-4 lg:col-span-2">
        <Bar label="Quality of work" value={p.avg_quality} max={5} text={`${p.avg_quality?.toFixed(1)} / 5`} />
        <Bar label="Value for money" value={p.avg_pricing} max={5} text={`${p.avg_pricing?.toFixed(1)} / 5`} />
        <Bar
          label="Punctuality (wedding-day check-ins)"
          value={p.punctuality_pct}
          max={100}
          text={`${p.punctuality_pct}% on time`}
          hint={
            p.punctuality_pct == null
              ? undefined
              : `${p.arrivals_counted} arrival${p.arrivals_counted === 1 ? '' : 's'} counted · average delay ${p.avg_delay_min ?? 0} min`
          }
        />
        <Bar label="Punctuality (planner rating)" value={p.avg_punctuality_rating} max={5} text={`${p.avg_punctuality_rating?.toFixed(1)} / 5`} />
      </Card>
    </div>
  )
}
