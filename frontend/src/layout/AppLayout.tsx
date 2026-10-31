import {
  Bell,
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
import { useState, type FormEvent } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { cn } from '@/components/common'
import { LiveStatus } from '@/live/LiveStatus'
import { useLogin } from '@/login/LoginContext'
import { NotificationBell } from '@/pages/notifications/NotificationBell'

const NAV: { to: string; label: string; icon: LucideIcon; end?: boolean }[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/enquiries', label: 'Enquiries', icon: MessageCircle },
  { to: '/clients', label: 'Clients', icon: Users },
  { to: '/weddings', label: 'Weddings', icon: CalendarHeart },
  { to: '/vendors', label: 'Vendors', icon: Store },
  { to: '/quotations', label: 'Quotations', icon: FileText },
  { to: '/incidents', label: 'Incidents', icon: TriangleAlert },
  { to: '/payments', label: 'Payments', icon: Wallet },
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
  // start with a slim sidebar on small screens
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 768)
  const [search, setSearch] = useState('')

  // the search box looks up couples in the enquiries list
  const onSearch = (event: FormEvent) => {
    event.preventDefault()
    navigate(search ? `/enquiries?q=${encodeURIComponent(search)}` : '/enquiries')
  }

  return (
    <div className="flex h-full">
      <aside className={cn('flex flex-col bg-sidebar text-slate-300 transition-all', collapsed ? 'w-[72px]' : 'w-64')}>
        <div className="flex h-16 items-center justify-between px-4">
          {!collapsed && (
            <div className="leading-tight">
              <div className="font-semibold tracking-wide text-white">KalyaanaMaalai</div>
              <div className="text-[11px] text-slate-400">Shaandaar Events</div>
            </div>
          )}
          <button
            aria-label="Toggle sidebar"
            className="rounded-lg p-2 text-slate-400 hover:bg-sidebar-hover hover:text-white"
            onClick={() => setCollapsed((c) => !c)}
          >
            <Menu size={18} />
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={label}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive ? 'bg-brand-500 text-white shadow-md shadow-brand-500/30' : 'hover:bg-sidebar-hover hover:text-white',
                  collapsed && 'justify-center',
                )
              }
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>
        {!collapsed && (
          <div className="m-3 rounded-xl bg-sidebar-hover p-3 text-xs text-slate-400">
            Planning weddings, one detail at a time.
          </div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center gap-4 border-b border-slate-200/70 bg-white px-6">
          <form onSubmit={onSearch} className="relative max-w-md flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              aria-label="Search couples"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search couples by name or phone…"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:bg-white focus:ring-2 focus:ring-brand-100"
            />
          </form>
          <div className="ml-auto flex items-center gap-4">
            <LiveStatus />
            <NotificationBell />
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
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
              className="rounded-full p-2 text-slate-500 hover:bg-slate-100"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
