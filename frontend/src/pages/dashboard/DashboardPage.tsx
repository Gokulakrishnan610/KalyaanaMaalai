import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  Bell,
  CalendarHeart,
  FileText,
  IndianRupee,
  ListChecks,
  Receipt,
  Store,
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
import { Badge, Card, CardTitle, CountUp, EmptyState, Emblem, ErrorState, Spinner } from '@/components/common'
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

function Kpi({ label, value, hint, icon: Icon, tint }: { label: string; value: ReactNode; hint: ReactNode; icon: LucideIcon; tint: keyof typeof TINTS }) {
  return (
    <div className="lift group relative flex items-center gap-4 overflow-hidden rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
      {/* a soft tinted glow in the corner, the same colour as the icon */}
      <div className={`pointer-events-none absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-60 blur-2xl transition-opacity group-hover:opacity-100 ${TINTS[tint].split(' ')[0]}`} aria-hidden="true" />
      <div className={`relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-6 ${TINTS[tint]}`}>
        <Icon size={22} />
      </div>
      <div className="relative min-w-0">
        <div className="text-xs font-medium text-slate-500">{label}</div>
        <div className="truncate text-2xl font-semibold">{value}</div>
        <div className="text-xs text-slate-500">{hint}</div>
      </div>
    </div>
  )
}

const QUICK_LINKS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/enquiries', label: 'New enquiry', icon: UserPlus },
  { to: '/weddings', label: 'Weddings', icon: CalendarHeart },
  { to: '/vendors', label: 'Vendors', icon: Store },
  { to: '/quotations', label: 'Quotations', icon: FileText },
]

function greeting() {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

/** The big welcome card at the top of the homepage: greeting, the next wedding and shortcuts. */
function Hero({ name, nextWedding, pipeline, openEnquiries }: {
  name: string
  nextWedding: { title: string; date: string; progress_pct: number } | null
  pipeline: number
  openEnquiries: number
}) {
  const days = nextWedding ? Math.ceil((new Date(nextWedding.date).getTime() - Date.now()) / 86_400_000) : null
  return (
    <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#2a1530] via-[#5b1d44] to-brand-600 p-6 text-white shadow-xl shadow-brand-500/20 sm:p-8">
      {/* decorative light and rings */}
      <div className="pointer-events-none absolute -right-16 -top-20 h-72 w-72 rounded-full bg-brand-500/40 blur-3xl" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-violet-500/30 blur-3xl" aria-hidden="true" />
      <Emblem className="float pointer-events-none absolute -right-4 top-1/2 hidden h-52 w-52 -translate-y-1/2 opacity-25 sm:block" />
      {[['58%', '16%', 0], ['72%', '70%', 1.2], ['40%', '78%', 2.1]].map(([x, y, d], i) => (
        <svg key={i} viewBox="0 0 24 24" className="twinkle pointer-events-none absolute h-4 w-4 text-amber-300" style={{ left: x as string, top: y as string, animationDelay: `${d}s` }} aria-hidden="true">
          <path fill="currentColor" d="M12 0l2.6 9.4L24 12l-9.4 2.6L12 24l-2.6-9.4L0 12l9.4-2.6z" />
        </svg>
      ))}

      <div className="relative max-w-2xl">
        <p className="text-sm font-medium text-rose-100/90">
          {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })}
        </p>
        <h1 className="mt-1 text-3xl font-bold sm:text-4xl" style={{ background: 'none', color: 'white', WebkitTextFillColor: 'white', animation: 'none' }}>
          {greeting()}, {name}!
        </h1>
        <p className="mt-2 text-sm text-rose-100/90">
          {nextWedding && days !== null ? (
            days >= 0 ? (
              <>
                Your next wedding, <strong className="text-white">{nextWedding.title}</strong>, is in{' '}
                <strong className="text-white">{days} day{days === 1 ? '' : 's'}</strong> and {nextWedding.progress_pct}% planned.
              </>
            ) : (
              <>
                <strong className="text-white">{nextWedding.title}</strong> is under way.
              </>
            )
          ) : (
            'No weddings are lined up yet. Convert an enquiry to start one.'
          )}{' '}
          {openEnquiries > 0 && (
            <>
              {openEnquiries} open enquir{openEnquiries === 1 ? 'y is' : 'ies are'} waiting
              {pipeline > 0 && (
                <>
                  , worth about <strong className="text-white">{formatINR(pipeline)}</strong>
                </>
              )}
              .
            </>
          )}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          {QUICK_LINKS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="group inline-flex items-center gap-2 rounded-xl bg-white/12 px-3.5 py-2 text-sm font-medium text-white ring-1 ring-white/20 backdrop-blur transition-all hover:-translate-y-0.5 hover:bg-white hover:text-brand-700"
            >
              <Icon size={16} />
              {label}
              <ArrowRight size={14} className="-ml-1 w-0 opacity-0 transition-all group-hover:ml-0 group-hover:w-3.5 group-hover:opacity-100" />
            </Link>
          ))}
        </div>
      </div>
    </section>
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

  // the wedding coming up soonest (or happening now), for the welcome card
  const today = new Date().toISOString().slice(0, 10)
  const nextWedding = [...data.per_wedding].filter((w) => w.date >= today).sort((a, b) => a.date.localeCompare(b.date))[0] ?? null
  const sourceData = data.enquiries_by_source.map((s) => ({ name: sourceInfo(s.source).label, count: s.count }))
  const weddingData = data.per_wedding.map((w) => ({
    name: w.title.length > 14 ? `${w.title.slice(0, 14)}…` : w.title,
    Revenue: w.revenue_paise / 100,
    Expenses: w.expense_paise / 100,
  }))

  return (
    <div className="space-y-6">
      <Hero
        name={user?.name.split(' ')[0] ?? ''}
        nextWedding={nextWedding}
        pipeline={data.pipeline_expected_paise}
        openEnquiries={data.active_enquiries}
      />

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
        <Kpi label="Total weddings" value={<CountUp value={data.total_weddings} />} hint={`${data.ongoing_weddings} ongoing`} icon={CalendarHeart} tint="peach" />
        <Kpi label="Total revenue" value={<CountUp value={data.total_revenue_paise} format={formatINR} />} hint={`${formatINR(data.total_received_paise)} received`} icon={Wallet} tint="lavender" />
        <Kpi label="Total expenses" value={<CountUp value={data.total_expenses_paise} format={formatINR} />} hint={`Profit ${formatINR(data.total_profit_paise)}`} icon={Receipt} tint="mint" />
        <Kpi
          label="Active tasks"
          value={<CountUp value={data.open_tasks} />}
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
                    <div className="bar-grow h-full rounded-full bg-gradient-to-r from-brand-500 to-violet-500" style={{ width: `${w.progress_pct}%` }} />
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
