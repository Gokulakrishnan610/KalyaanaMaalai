import { Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LogOut } from 'lucide-react'
import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { get, VENDOR_TOKEN_KEY } from '@/api/client'
import { cn, Emblem, Spinner } from '@/components/common'
import type { VendorMe } from './types'

const TABS = [
  { to: '/vendor', label: 'My bookings', end: true },
  { to: '/vendor/requests', label: 'Quotation requests', end: false },
  { to: '/vendor/payments', label: 'Payments', end: false },
  { to: '/vendor/account', label: 'My account', end: false },
]

/** The vendor's own area of the main site: a simple top bar instead of the team's sidebar. */
export function VendorLayout() {
  const navigate = useNavigate()
  const signedIn = Boolean(localStorage.getItem(VENDOR_TOKEN_KEY))
  const { data } = useQuery({ queryKey: ['vendor-me'], queryFn: () => get<VendorMe>('/portal/vendor/me/'), enabled: signedIn })
  if (!signedIn) return <Navigate to="/login" replace />

  const logout = () => {
    localStorage.removeItem(VENDOR_TOKEN_KEY)
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3">
            <Emblem className="h-9 w-9" />
            <div>
              <div className="font-semibold leading-tight">{data?.vendor.name ?? 'Vendor'}</div>
              <div className="text-xs text-slate-500">{data ? `${data.vendor.category} · Shaandaar Events vendor` : 'Shaandaar Events vendor'}</div>
            </div>
          </div>
          <button onClick={logout} className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900">
            <LogOut size={16} /> Sign out
          </button>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.end}
              className={({ isActive }) =>
                cn('-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium', isActive ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800')
              }
            >
              {t.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{data ? <Suspense fallback={<Spinner />}><Outlet /></Suspense> : <Spinner />}</main>
    </div>
  )
}
