import { useQuery } from '@tanstack/react-query'
import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'
import { get, type Page } from '@/api/client'
import { Badge, Button, Card, EmptyState, ErrorState, Spinner, Table, Td, Th, cn } from '@/components/common'
import { Stars } from './Stars'
import type { Vendor } from './types'
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
  const q = useDeferredValue(search)
  const cityFilter = useDeferredValue(city)
  const { data: categories } = useVendorCategories()

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['vendors', { q, cityFilter, categoryId, page }],
    queryFn: () =>
      get<Page<Vendor>>('/vendors/', {
        q: q || undefined,
        city: cityFilter || undefined,
        category_id: categoryId ?? undefined,
        page,
        limit: PAGE_SIZE,
      }),
    placeholderData: (previous) => previous,
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

      <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Filter by category">
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
        <input
          aria-label="Search vendors"
          placeholder="Search name, contact or phone"
          value={search}
          onChange={(e) => resetPage(setSearch)(e.target.value)}
          className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <input
          aria-label="Filter by city"
          placeholder="City"
          value={city}
          onChange={(e) => resetPage(setCity)(e.target.value)}
          className="w-40 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
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
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {data.results.map((v) => (
                <Link key={v.id} to={`/vendors/${v.id}`} className="block rounded-xl focus-visible:outline-2 focus-visible:outline-brand-500">
                  <Card lift className="h-full">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-violet-500 text-sm font-bold text-white shadow-md shadow-brand-500/25">
                          {v.name.charAt(0).toUpperCase()}
                        </span>
                        <h2 className="font-semibold text-slate-900">{v.name}</h2>
                      </div>
                      <Badge tone="brand">{v.category_name}</Badge>
                    </div>
                    <div className="mt-2">
                      <Stars value={v.avg_rating} />
                    </div>
                    <dl className="mt-3 space-y-0.5 text-sm text-slate-600">
                      <div>{v.contact_person || '—'}</div>
                      <div>{v.phone}</div>
                      <div>{v.city || 'City not set'}</div>
                    </dl>
                    <p className="mt-3 text-xs text-slate-500">
                      {v.weddings_count} wedding{v.weddings_count === 1 ? '' : 's'} with us
                    </p>
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

      {adding && (
        <VendorForm
          open
          defaultCategoryId={categoryId ?? undefined}
          onClose={() => setAdding(false)}
          onSaved={(v) =>
            v.duplicate_warning &&
            setNotice(`Saved, but a vendor named "${v.name}" with the same phone number already exists. Check it is not a duplicate.`)
          }
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
        'rounded-full border px-3 py-1 text-sm transition-colors',
        active ? 'border-brand-500 bg-brand-50 font-medium text-brand-700' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50',
      )}
    >
      {children}
    </button>
  )
}
