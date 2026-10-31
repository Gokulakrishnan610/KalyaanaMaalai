import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import { Badge, Card, CardTitle } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { ROLE_LABELS, type Checkin, type WeddingDetail } from './types'

interface Progress {
  total: number
  done: number
  pct: number
  overdue: number
}

function ProgressRing({ pct }: { pct: number }) {
  const radius = 42
  const circumference = 2 * Math.PI * radius
  return (
    <svg width="110" height="110" viewBox="0 0 110 110" role="img" aria-label={`${pct}% done`}>
      <circle cx="55" cy="55" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="10" />
      <circle
        cx="55"
        cy="55"
        r={radius}
        fill="none"
        stroke="#c2185b"
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - pct / 100)}
        transform="rotate(-90 55 55)"
      />
      <text x="55" y="61" textAnchor="middle" className="fill-slate-800 text-xl font-semibold">
        {pct}%
      </text>
    </svg>
  )
}

function countdown(startDate: string): string {
  const days = Math.ceil((new Date(startDate + 'T00:00:00').getTime() - Date.now()) / 86_400_000)
  if (days > 1) return `${days} days to go`
  if (days === 1) return 'Tomorrow'
  if (days === 0) return 'Today'
  return `${-days} day${days === -1 ? '' : 's'} ago`
}

export function OverviewTab({ wedding }: { wedding: WeddingDetail }) {
  const progress = useQuery({
    queryKey: ['wedding-progress', wedding.id],
    queryFn: () => get<Progress>(`/weddings/${wedding.id}/progress/`),
  })
  const checkins = useQuery({
    queryKey: ['checkins', wedding.id],
    queryFn: () => get<Checkin[]>(`/weddings/${wedding.id}/checkins/`),
  })
  const money = useQuery({
    queryKey: ['wedding-finance', wedding.id],
    queryFn: () =>
      get<{ revenue: { invoiced: number; received: number; outstanding: number }; expenses: { planned: number; paid: number; outstanding: number }; estimated_profit: number; margin_pct: number | null }>(
        `/weddings/${wedding.id}/finance/`,
      ),
  })

  const arrived = checkins.data?.filter((c) => c.status !== 'PENDING' || c.actual_arrival).length ?? 0
  const late = checkins.data?.filter((c) => c.status === 'LATE').length ?? 0

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardTitle>Key information</CardTitle>
        <dl className="space-y-1.5 text-sm">
          <Row label="Client" value={wedding.client_name} />
          <Row label="Dates" value={`${formatDate(wedding.start_date)} – ${formatDate(wedding.end_date)}`} />
          <Row label="City" value={wedding.city} />
          <Row label="Guests" value={`${wedding.guest_count} (contracted ${wedding.contracted_guests})`} />
          <Row label="Rate per extra guest" value={formatINR(wedding.per_guest_rate_paise)} />
          <Row label="Budget" value={formatINR(wedding.budget_paise)} />
        </dl>
      </Card>

      <Card className="flex flex-col items-center justify-center text-center">
        <CardTitle>Task progress</CardTitle>
        <ProgressRing pct={progress.data?.pct ?? wedding.progress_pct} />
        <p className="mt-2 text-sm text-slate-600">
          {progress.data ? `${progress.data.done} of ${progress.data.total} tasks done` : 'Loading…'}
        </p>
        {progress.data && progress.data.overdue > 0 && (
          <div className="mt-1">
            <Badge tone="red">{progress.data.overdue} overdue</Badge>
          </div>
        )}
        <p className="mt-3 text-lg font-semibold text-brand-700">{countdown(wedding.start_date)}</p>
      </Card>

      <Card>
        <CardTitle>Team</CardTitle>
        {wedding.assignments.length === 0 ? (
          <p className="text-sm text-slate-500">Nobody is assigned yet.</p>
        ) : (
          <ul className="space-y-1.5 text-sm">
            {wedding.assignments.map((m) => (
              <li key={m.id} className="flex justify-between">
                <span>{m.user_name}</span>
                <span className="text-slate-500">{ROLE_LABELS[m.role_label] ?? m.role_label}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <CardTitle>Vendors</CardTitle>
        <p className="text-sm text-slate-600">Open the Vendors tab for quotes and bookings.</p>
        <p className="mt-2 text-sm">
          Arrival check-ins: {arrived} of {checkins.data?.length ?? 0} arrived
          {late > 0 && <span className="ml-2"><Badge tone="red">{late} late</Badge></span>}
        </p>
      </Card>

      <Card className="lg:col-span-2">
        <div className="mb-3 flex items-center justify-between">
          <CardTitle className="mb-0">Money</CardTitle>
          <Link to="/payments" className="text-xs font-medium text-brand-600 hover:text-brand-700">Open payments</Link>
        </div>
        {!money.data ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            {[
              ['Invoiced to the couple', formatINR(money.data.revenue.invoiced)],
              ['Received', formatINR(money.data.revenue.received)],
              ['Owed to vendors', formatINR(money.data.expenses.outstanding)],
              ['Expected profit', `${formatINR(money.data.estimated_profit)}${money.data.margin_pct !== null ? ` (${money.data.margin_pct}%)` : ''}`],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="num mt-1 text-base font-semibold text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  )
}
