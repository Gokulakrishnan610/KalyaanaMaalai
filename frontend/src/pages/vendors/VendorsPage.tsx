import { MapPin, Phone, Star, UserRound } from 'lucide-react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { get, type Page } from '@/api/client'
import { Button, Card, EmptyState, ErrorState, SearchBox, Spinner, Table, Td, Th, cn } from '@/components/common'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { Stars } from './Stars'
import type { Vendor } from './types'
import { LoginDetailsModal, type VendorLogin } from './LoginDetailsModal'
import { VendorForm } from './VendorForm'
import { useVendorCategories } from './useVendorCategories'

const PAGE_SIZE = 12

export default function VendorsPage() {
  const [search, setSearch] = useState('')
  const [city, setCity] = useState('')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [view, setView] = useState<'cards' | 'table'>('cards')
  const [page, setPage] = useState(1)
  const [adding, setAdding] = useState(false)
  const [notice, setNotice] = useState('')
  const [newLogin, setNewLogin] = useState<{ name: string; login: VendorLogin } | null>(null)
  // wait until typing pauses before asking the server
  const q = useDebouncedValue(search.trim())
  const cityFilter = useDebouncedValue(city.trim())
  const { data: categories } = useVendorCategories()

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['vendors', { q, cityFilter, categoryId, page }],
    queryFn: ({ signal }) =>
      get<Page<Vendor>>(
        '/vendors/',
        { q: q || undefined, city: cityFilter || undefined, category_id: categoryId ?? undefined, page, limit: PAGE_SIZE },
        signal,
      ),
    placeholderData: keepPreviousData,
  })

  const resetPage = <T,>(setter: (v: T) => void) => (value: T) => {
    setter(value)
    setPage(1)
  }
  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Vendors</h1>
          <p className="text-sm text-slate-500">Caterers, decorators, DJs and everyone else we hire for weddings.</p>
        </div>
        <Button onClick={() => setAdding(true)}>+ Add vendor</Button>
      </div>

      {notice && (
        <div role="status" className="mb-4 flex items-start justify-between rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          {notice}
          <button className="ml-4 font-medium underline" onClick={() => setNotice('')}>
            Dismiss
          </button>
        </div>
      )}

      <div className="-mx-1 mb-3 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]" role="group" aria-label="Filter by category">
        <Chip active={categoryId === null} onClick={() => resetPage(setCategoryId)(null)}>
          All
        </Chip>
        {categories?.map((c) => (
          <Chip key={c.id} active={categoryId === c.id} onClick={() => resetPage(setCategoryId)(c.id)}>
            {c.name}
          </Chip>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <SearchBox
          label="Search vendors"
          placeholder="Search name, contact or phone"
          value={search}
          onChange={resetPage(setSearch)}
          busy={search.trim() !== q || (isFetching && !!q)}
          className="w-64"
        />
        <SearchBox
          label="Filter by city"
          placeholder="City"
          value={city}
          onChange={resetPage(setCity)}
          busy={city.trim() !== cityFilter}
          className="w-44"
        />
        <div className="ml-auto flex overflow-hidden rounded-lg border border-slate-300 text-sm">
          {(['cards', 'table'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              aria-pressed={view === v}
              className={cn('px-3 py-1.5 capitalize', view === v ? 'bg-brand-50 font-medium text-brand-700' : 'bg-white text-slate-600')}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && data.results.length === 0 && (
        <EmptyState
          title="No vendors found"
          hint={q || cityFilter || categoryId ? 'Try clearing the filters.' : 'Add the first vendor to get started.'}
          action={<Button onClick={() => setAdding(true)}>+ Add vendor</Button>}
        />
      )}

      {data && data.results.length > 0 && (
        <div className={cn(isFetching && 'opacity-70 transition-opacity')}>
          {view === 'cards' ? (
            <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">
              {data.results.map((v) => (
                <Link key={v.id} to={`/vendors/${v.id}`} className="block rounded-xl focus-visible:outline-2 focus-visible:outline-brand-500">
                  <Card lift className="flex h-full flex-col p-4">
                    <div className="flex items-start gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-sm font-semibold text-slate-700">
                        {v.name.charAt(0).toUpperCase()}
                      </span>
                      <div className="min-w-0 flex-1">
                        <h2 className="truncate text-sm font-semibold text-slate-900" title={v.name}>{v.name}</h2>
                        <p className="text-xs text-slate-500">{v.category_name}</p>
                      </div>
                      {v.avg_rating !== null && (
                        <span className="num flex shrink-0 items-center gap-1 text-xs font-medium text-slate-700">
                          <Star size={13} className="fill-amber-400 text-amber-400" /> {v.avg_rating.toFixed(1)}
                        </span>
                      )}
                    </div>
                    <div className="mt-3 space-y-1.5 text-xs text-slate-600">
                      <div className="flex items-center gap-2"><UserRound size={13} className="shrink-0 text-slate-400" /><span className="truncate">{v.contact_person || 'No contact person'}</span></div>
                      <div className="flex items-center gap-2"><Phone size={13} className="shrink-0 text-slate-400" /><span className="num">{v.phone || 'No phone'}</span></div>
                      <div className="flex items-center gap-2"><MapPin size={13} className="shrink-0 text-slate-400" /><span className="truncate">{v.city || 'City not set'}</span></div>
                    </div>
                    <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500" style={{ marginTop: '0.875rem' }}>
                      <span>{v.weddings_count} wedding{v.weddings_count === 1 ? '' : 's'} with us</span>
                      {v.portal_account !== 'none' && <span className="text-emerald-600">Has login</span>}
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Vendor</Th>
                  <Th>Category</Th>
                  <Th>City</Th>
                  <Th>Phone</Th>
                  <Th>Rating</Th>
                  <Th className="text-right">Weddings</Th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((v) => (
                  <tr key={v.id} className="hover:bg-slate-50">
                    <Td>
                      <Link className="font-medium text-brand-700 hover:underline" to={`/vendors/${v.id}`}>
                        {v.name}
                      </Link>
                    </Td>
                    <Td>{v.category_name}</Td>
                    <Td>{v.city || '—'}</Td>
                    <Td>{v.phone}</Td>
                    <Td>
                      <Stars value={v.avg_rating} />
                    </Td>
                    <Td className="text-right">{v.weddings_count}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}

          {pages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-3 text-sm">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <span className="text-slate-500">
                Page {page} of {pages} · {data.count} vendors
              </span>
              <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
                Next
              </Button>
            </div>
          )}
        </div>
      )}

      {newLogin && <LoginDetailsModal vendorName={newLogin.name} login={newLogin.login} onClose={() => setNewLogin(null)} />}
      {adding && (
        <VendorForm
          open
          defaultCategoryId={categoryId ?? undefined}
          onClose={() => setAdding(false)}
          onSaved={(v) => {
            if (v.login) setNewLogin({ name: v.name, login: v.login })
            if (v.login_error) setNotice(v.login_error)
            if (v.duplicate_warning) setNotice(`Saved, but a vendor named "${v.name}" with the same phone number already exists. Check it is not a duplicate.`)
          }}
        />
      )}
    </div>
  )
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'h-8 shrink-0 whitespace-nowrap rounded-lg border px-3 text-sm transition-colors',
        active ? 'border-slate-900 bg-slate-900 font-medium text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900',
      )}
    >
      {children}
    </button>
  )
}
