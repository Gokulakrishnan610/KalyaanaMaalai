import {
  Bell,
  FileSignature,
  Mail,
  CalendarHeart,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
  Search,
  Store,
  Users,
  Wallet,
  FileText,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { useState, type FormEvent, Suspense } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Emblem, Spinner, cn } from '@/components/common'
import { LiveStatus } from '@/live/LiveStatus'
import { useLogin } from '@/login/LoginContext'
import { NotificationBell } from '@/pages/notifications/NotificationBell'

type NavItem = { to: string; label: string; icon: LucideIcon; end?: boolean; group?: string }
// grouped like the work itself: winning couples, running weddings, money, and the system's messages
const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/enquiries', label: 'Enquiries', icon: MessageCircle, group: 'Sales' },
  { to: '/clients', label: 'Clients', icon: Users },
  { to: '/weddings', label: 'Weddings', icon: CalendarHeart, group: 'Weddings' },
  { to: '/vendors', label: 'Vendors', icon: Store },
  { to: '/quotations', label: 'Quotations', icon: FileText },
  { to: '/incidents', label: 'Incidents', icon: TriangleAlert },
  { to: '/payments', label: 'Payments', icon: Wallet, group: 'Money' },
  { to: '/agreements', label: 'Agreements', icon: FileSignature },
  { to: '/emails', label: 'Emails', icon: Mail, group: 'Messages' },
  { to: '/notifications', label: 'Notifications', icon: Bell },
]

function initials(name: string | undefined) {
  return (name ?? '?')
    .split(' ')
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function AppLayout() {
  const { user, logout } = useLogin()
  const navigate = useNavigate()
  const location = useLocation()
  // start with a slim sidebar on small screens
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 768)
  const [search, setSearch] = useState('')

  // the search box looks up couples in the enquiries list
  const onSearch = (event: FormEvent) => {
    event.preventDefault()
    navigate(search ? `/enquiries?q=${encodeURIComponent(search)}` : '/enquiries')
  }

  return (
    <div className="app-shell relative isolate flex h-screen overflow-hidden">
      {/* soft drifting colour behind everything */}
      <div className="aurora pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
        <span className="-left-24 top-10 h-96 w-96 bg-brand-100" />
        <span className="right-0 top-1/3 h-[28rem] w-[28rem] bg-lavender" style={{ animationDelay: '-7s' }} />
        <span className="bottom-0 left-1/3 h-80 w-80 bg-sand" style={{ animationDelay: '-13s' }} />
      </div>
      <aside
        className={cn(
          'relative flex flex-col overflow-y-auto border-r border-black/20 bg-sidebar text-slate-400 transition-[width] duration-200 ease-out',
          collapsed ? 'w-[68px]' : 'w-60',
        )}
      >
        <div className={cn('flex items-center px-4', collapsed ? 'flex-col gap-1 py-3' : 'h-14 justify-between')}>
          {/* the logo always leads back to the homepage, from every screen */}
          <Link
            to="/"
            aria-label="KalyaanaMaalai home"
            title="Go to the homepage"
            className="group flex items-center gap-2.5 rounded-xl leading-tight outline-offset-4"
          >
            <Emblem className="h-8 w-8 shrink-0" />
            {!collapsed && (
              <div>
                <div className="font-semibold tracking-wide text-white">KalyaanaMaalai</div>
                <div className="text-[11px] text-slate-400">Shaandaar Events</div>
              </div>
            )}
          </Link>
          <button
            aria-label="Toggle sidebar"
            className="rounded-lg p-2 text-slate-400 hover:bg-sidebar-hover hover:text-white"
            onClick={() => setCollapsed((c) => !c)}
          >
            <Menu size={18} />
          </button>
        </div>
        <nav className="flex-1 px-3 pb-3">
          {NAV.map(({ to, label, icon: Icon, end, group }) => (
            <div key={to}>
              {group && (collapsed ? <div className="mx-2 my-3 border-t border-white/10" /> : (
                <div className="px-3 pb-1.5 pt-5 text-[11px] font-medium uppercase tracking-wider text-slate-500">{group}</div>
              ))}
              <NavLink
                to={to}
                end={end}
                title={label}
                className={({ isActive }) =>
                  cn(
                    'relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive ? 'bg-white/10 text-white' : 'hover:bg-sidebar-hover hover:text-slate-100',
                    collapsed && 'justify-center',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-brand-500" aria-hidden="true" />}
                    <Icon size={17} className="shrink-0" />
                    {!collapsed && label}
                  </>
                )}
              </NavLink>
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-4 border-b border-slate-200 bg-white px-6">
          <form onSubmit={onSearch} className="relative max-w-md flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              aria-label="Search couples"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search couples by name or phone…"
              className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm outline-none placeholder:text-slate-400 focus:border-brand-500 focus:bg-white focus:ring-2 focus:ring-brand-100"
            />
          </form>
          <div className="ml-auto flex items-center gap-4">
            <LiveStatus />
            <NotificationBell />
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white">
                {initials(user?.name)}
              </div>
              <div className="hidden text-sm leading-tight sm:block">
                <div className="font-medium">{user?.name}</div>
                <div className="text-xs capitalize text-slate-500">{user?.role.toLowerCase()}</div>
              </div>
            </div>
            <button
              aria-label="Log out"
              title="Log out"
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto px-6 py-6 lg:px-8">
          {/* keyed by address, so every screen change replays the entrance animation */}
          <div key={location.pathname} className="page-enter mx-auto max-w-[1400px]">
            <Suspense fallback={<Spinner />}><Outlet /></Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}
