import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { cn } from '@/components/common'
import { useLogin } from '@/login/LoginContext'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/enquiries', label: 'Enquiries' },
  { to: '/clients', label: 'Clients' },
  { to: '/weddings', label: 'Weddings' },
  { to: '/vendors', label: 'Vendors' },
  { to: '/quotations', label: 'Quotations' },
  { to: '/payments', label: 'Payments' },
  { to: '/notifications', label: 'Notifications' },
]

export function AppLayout() {
  const { user, logout } = useLogin()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-full">
      <aside className={cn('flex flex-col border-r border-slate-200 bg-white transition-all', collapsed ? 'w-16' : 'w-60')}>
        <div className="flex h-14 items-center justify-between px-4">
          {!collapsed && <span className="font-semibold text-brand-600">KalyaanaMaalai</span>}
          <button
            aria-label="Toggle sidebar"
            className="rounded p-1 text-slate-500 hover:bg-slate-100"
            onClick={() => setCollapsed((c) => !c)}
          >
            ☰
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-2 py-2">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={item.label}
              className={({ isActive }) =>
                cn(
                  'block rounded-lg px-3 py-2 text-sm font-medium',
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100',
                  collapsed && 'truncate text-center',
                )
              }
            >
              {collapsed ? item.label[0] : item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-4 border-b border-slate-200 bg-white px-6">
          {/* Member 4 plugs the notification bell in here */}
          <div id="notification-bell-slot" />
          <div className="text-right text-sm leading-tight">
            <div className="font-medium">{user?.name}</div>
            <div className="text-xs text-slate-500">{user?.role}</div>
          </div>
          <button
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            Log out
          </button>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
