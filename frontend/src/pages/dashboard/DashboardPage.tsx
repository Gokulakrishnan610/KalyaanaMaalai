import { useQuery } from '@tanstack/react-query'
import {
  Bell,
  CalendarHeart,
  IndianRupee,
  ListChecks,
  Receipt,
  Truck,
  UserPlus,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { get } from '@/api/client'
import { Badge, Card, CardTitle, EmptyState, ErrorState, Spinner } from '@/components/common'
import { formatDate, formatDateTime, timeAgo } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { sourceInfo, type Source } from '@/pages/enquiries/types'

interface Summary {
  active_enquiries: number
  open_incidents: number
  critical_incidents: number
  recent_incidents: { id: number; title: string; wedding_title: string; severity: string; status: string; assigned_to_name: string }[]
  overdue_follow_ups: number
  pipeline_expected_paise: number
  upcoming_follow_ups: { id: number; enquiry_id: number; couple_name: string; kind: string; summary: string; due_at: string; overdue: boolean }[]
  enquiries_by_source: { source: Source; count: number }[]
  conversion_rate: number
  total_weddings: number
  ongoing_weddings: number
  open_tasks: number
  overdue_tasks: number
  recent_activity: { kind: 'enquiry' | 'payment' | 'vendor' | 'alert'; text: string; at: string }[]
  total_revenue_paise: number
  total_received_paise: number
  total_expenses_paise: number
  total_profit_paise: number
  outstanding_client_paise: number
  upcoming_vendor_payments: {
    expense_id: number
    wedding_title: string
    vendor_name: string
    description: string
    due_date: string
    outstanding_paise: number
    overdue: boolean
  }[]
  late_vendors_today: number
  upcoming_consultations: { id: number; couple_name: string; consultation_at: string }[]
  per_wedding: {
    wedding_id: number
    title: string
    client_name: string
    date: string
    revenue_paise: number
    expense_paise: number
    profit_paise: number
    margin_pct: number
    progress_pct: number
  }[]
}

const TINTS = {
  peach: 'bg-peach text-orange-600',
  lavender: 'bg-lavender text-violet-600',
  mint: 'bg-mint text-emerald-600',
  sand: 'bg-sand text-amber-600',
}

function Kpi({ label, value, hint, icon: Icon, tint }: { label: string; value: string; hint: ReactNode; icon: LucideIcon; tint: keyof typeof TINTS }) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
      <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${TINTS[tint]}`}>
        <Icon size={22} />
      </div>
      <div className="min-w-0">
        <div className="text-xs font-medium text-slate-500">{label}</div>
        <div className="truncate text-2xl font-semibold">{value}</div>
        <div className="text-xs text-slate-500">{hint}</div>
      </div>
    </div>
  )
}

const ACTIVITY_ICON: Record<Summary['recent_activity'][number]['kind'], { icon: LucideIcon; tint: string }> = {
  enquiry: { icon: UserPlus, tint: 'bg-sky-100 text-sky-600' },
  payment: { icon: IndianRupee, tint: 'bg-emerald-100 text-emerald-600' },
  vendor: { icon: Truck, tint: 'bg-amber-100 text-amber-600' },
  alert: { icon: Bell, tint: 'bg-rose-100 text-rose-600' },
}

export default function DashboardPage() {
  const { user, hasRole } = useLogin()
  const allowed = hasRole('PLANNER')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => get<Summary>('/dashboard/summary/'),
    enabled: allowed,
    refetchInterval: 30_000, // keeps the activity feed fresh
  })

  if (!allowed) {
    return (
      <div>
        <h1 className="mb-4 text-2xl font-semibold">Dashboard</h1>
        <EmptyState title="The dashboard is for the founder and planners" hint="Use the menu to open your tasks and weddings." />
      </div>
    )
  }
  if (isLoading) return <Spinner />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load the dashboard'} onRetry={refetch} />

  const sourceData = data.enquiries_by_source.map((s) => ({ name: sourceInfo(s.source).label, count: s.count }))
  const weddingData = data.per_wedding.map((w) => ({
    name: w.title.length > 14 ? `${w.title.slice(0, 14)}…` : w.title,
    Revenue: w.revenue_paise / 100,
    Expenses: w.expense_paise / 100,
  }))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold">Welcome back, {user?.name.split(' ')[0]}!</h1>
          <p className="text-sm text-slate-500">Here’s what’s happening with your weddings today.</p>
        </div>
        <div className="rounded-xl border border-slate-200/70 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm">
          {new Date().toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })}
        </div>
      </div>

      {data.late_vendors_today > 0 && (
        <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {data.late_vendors_today} vendor{data.late_vendors_today > 1 ? 's are' : ' is'} running late today.
        </div>
      )}

      {data.critical_incidents > 0 && (
        <Link to="/incidents" role="alert" className="block rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {data.critical_incidents} serious incident{data.critical_incidents > 1 ? 's need' : ' needs'} attention. Open incidents →
        </Link>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Total weddings" value={String(data.total_weddings)} hint={`${data.ongoing_weddings} ongoing`} icon={CalendarHeart} tint="peach" />
        <Kpi label="Total revenue" value={formatINR(data.total_revenue_paise)} hint={`${formatINR(data.total_received_paise)} received`} icon={Wallet} tint="lavender" />
        <Kpi label="Total expenses" value={formatINR(data.total_expenses_paise)} hint={`Profit ${formatINR(data.total_profit_paise)}`} icon={Receipt} tint="mint" />
        <Kpi
          label="Active tasks"
          value={String(data.open_tasks)}
          hint={<span className={data.overdue_tasks ? 'font-medium text-red-600' : ''}>{data.overdue_tasks} overdue</span>}
          icon={ListChecks}
          tint="sand"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <CardTitle className="mb-0 text-base">Ongoing weddings</CardTitle>
            <Link to="/weddings" className="text-xs font-medium text-brand-600 hover:underline">View all</Link>
          </div>
          {data.per_wedding.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">No weddings yet. Convert an enquiry to start one.</p>
          ) : (
            <ul className="space-y-4">
              {data.per_wedding.map((w) => (
                <li key={w.wedding_id}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{w.title}</span>
                    <span className="text-xs font-medium text-brand-600">{w.progress_pct}%</span>
                  </div>
                  <div className="text-xs text-slate-500">{w.client_name} · {formatDate(w.date)}</div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-brand-500" style={{ width: `${w.progress_pct}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardTitle className="text-base">Revenue vs expenses</CardTitle>
          {weddingData.length === 0 ? (
            <p className="py-10 text-center text-sm text-slate-500">Nothing to compare yet.</p>
          ) : (
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weddingData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" fontSize={11} />
                  <YAxis fontSize={11} tickFormatter={(v: number) => (v >= 100000 ? `${v / 100000}L` : String(v))} />
                  <Tooltip formatter={(v) => formatINR(Number(v) * 100)} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Revenue" fill="#e5395c" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Expenses" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <CardTitle className="mb-0 text-base">Recent activity</CardTitle>
            <span className="flex items-center gap-1 text-xs text-emerald-600">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" /> Live
            </span>
          </div>
          {data.recent_activity.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">Nothing has happened yet.</p>
          ) : (
            <ul className="space-y-3">
              {data.recent_activity.map((item, index) => {
                const { icon: Icon, tint } = ACTIVITY_ICON[item.kind]
                return (
                  <li key={index} className="flex items-start gap-3 text-sm">
                    <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${tint}`}>
                      <Icon size={15} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block leading-snug">{item.text}</span>
                      <span className="text-xs text-slate-400">{timeAgo(item.at)}</span>
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardTitle className="text-base">Where enquiries come from</CardTitle>
          {sourceData.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">No enquiries yet.</p>
          ) : (
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sourceData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" name="Enquiries" fill="#e5395c" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="mt-2 text-xs text-slate-500">
            {data.active_enquiries} open enquiries · {data.conversion_rate}% became clients · expected pipeline{' '}
            {formatINR(data.pipeline_expected_paise)}
          </p>
        </Card>

        <Card>
          <div className="mb-3 flex items-center justify-between">
            <CardTitle className="mb-0 text-base">Follow-ups</CardTitle>
            {data.overdue_follow_ups > 0 && <Badge tone="red">{data.overdue_follow_ups} overdue</Badge>}
          </div>
          {data.upcoming_follow_ups.length === 0 ? (
            <p className="text-sm text-slate-500">Nothing planned. Add follow-ups on an enquiry.</p>
          ) : (
            <ul className="space-y-3 text-sm">
              {data.upcoming_follow_ups.map((f) => (
                <li key={f.id}>
                  <div className="flex justify-between gap-2">
                    <Link to={`/enquiries?q=${encodeURIComponent(f.couple_name)}`} className="font-medium hover:text-brand-600">
                      {f.couple_name}
                    </Link>
                    <span className={f.overdue ? 'font-medium text-red-600' : 'text-slate-500'}>{formatDateTime(f.due_at)}</span>
                  </div>
                  <div className="text-xs text-slate-500">{f.summary}</div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <CardTitle className="mb-0 text-base">Open incidents</CardTitle>
          <Link to="/incidents" className="text-xs font-medium text-brand-600 hover:underline">View all</Link>
        </div>
        {data.recent_incidents.length === 0 ? (
          <p className="text-sm text-slate-500">All clear. Nothing is open.</p>
        ) : (
          <ul className="space-y-3 text-sm">
            {data.recent_incidents.map((i) => (
              <li key={i.id}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{i.title}</span>
                  <Badge tone={i.severity === 'CRITICAL' ? 'red' : i.severity === 'HIGH' ? 'brand' : 'amber'}>{i.severity.toLowerCase()}</Badge>
                </div>
                <div className="text-xs text-slate-500">
                  {i.wedding_title} · {i.assigned_to_name ? `with ${i.assigned_to_name}` : 'not assigned yet'}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card>
        <CardTitle className="text-base">Upcoming consultations</CardTitle>
        {data.upcoming_consultations.length === 0 ? (
          <p className="text-sm text-slate-500">None booked.</p>
        ) : (
          <ul className="space-y-3 text-sm">
            {data.upcoming_consultations.map((c) => (
              <li key={c.id} className="flex justify-between gap-2">
                <span className="font-medium">{c.couple_name}</span>
                <span className="text-slate-500">{formatDateTime(c.consultation_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card>
        <CardTitle className="text-base">Vendor payments due this week</CardTitle>
        {data.upcoming_vendor_payments.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing due in the next 7 days.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {data.upcoming_vendor_payments.map((p) => (
              <li key={p.expense_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                <span>
                  <span className="font-medium">{p.vendor_name || p.description}</span>
                  <span className="text-slate-500"> · {p.wedding_title}</span>
                </span>
                <span className="flex items-center gap-3">
                  {formatDate(p.due_date)} {p.overdue && <Badge tone="red">Overdue</Badge>}
                  <span className="font-medium">{formatINR(p.outstanding_paise)}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      </div>
    </div>
  )
}
