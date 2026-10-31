import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { get, post, ApiError, type Page } from '@/api/client'
import { Button, Input, Modal, Select } from '@/components/common'
import { useVendorCategories } from '@/pages/vendors/useVendorCategories'
import type { Vendor } from '@/pages/vendors/types'
import type { QuotationRequest } from './types'

interface Props {
  /** Fixed when opened from a wedding's Vendors tab; otherwise the planner picks the wedding. */
  weddingId?: number
  onClose: () => void
  onCreated?: (request: QuotationRequest) => void
}

interface WeddingOption {
  id: number
  title: string
  guest_count: number
}

const CATERER_MINIMUM = 3

export function NewRequestForm({ weddingId, onClose, onCreated }: Props) {
  return (
    <Modal open title="New quotation request" onClose={onClose} wide>
      <FormBody weddingId={weddingId} onClose={onClose} onCreated={onCreated} />
    </Modal>
  )
}

function FormBody({ weddingId, onClose, onCreated }: Props) {
  const queryClient = useQueryClient()
  const { data: categories } = useVendorCategories()
  const [chosenWedding, setChosenWedding] = useState(weddingId ? String(weddingId) : '')
  const [categoryId, setCategoryId] = useState('')
  const [requirements, setRequirements] = useState('')
  const [guests, setGuests] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [invited, setInvited] = useState<number[]>([])
  const [warnings, setWarnings] = useState<string[] | null>(null)
  const [created, setCreated] = useState<QuotationRequest | null>(null)

  const weddings = useQuery({
    queryKey: ['wedding-options'],
    queryFn: () => get<Page<WeddingOption>>('/weddings/', { page_size: 200 }),
    enabled: !weddingId,
    retry: false,
  })
  const vendors = useQuery({
    queryKey: ['vendors', 'for-request', categoryId],
    queryFn: () => get<Page<Vendor>>('/vendors/', { category_id: categoryId, limit: 100 }),
    enabled: !!categoryId,
  })
  const categoryName = categories?.find((c) => String(c.id) === categoryId)?.name
  const fewCaterers = categoryName === 'Caterer' && invited.length > 0 && invited.length < CATERER_MINIMUM

  const create = useMutation({
    mutationFn: () =>
      post<QuotationRequest>(`/weddings/${chosenWedding}/quotation-requests/`, {
        category_id: Number(categoryId),
        requirements,
        guest_count: guests ? Number(guests) : undefined,
        due_date: dueDate || null,
        invited_vendor_ids: invited,
      }),
    onSuccess: (request) => {
      queryClient.invalidateQueries({ queryKey: ['quotation-requests'] })
      setCreated(request)
      if (request.warnings?.length) setWarnings(request.warnings)
      else finish(request)
    },
  })
  const errors = create.error instanceof ApiError ? create.error.fields : {}

  function finish(request: QuotationRequest) {
    onCreated?.(request)
    onClose()
  }

  function toggle(id: number) {
    setInvited((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]))
  }

  function submit(e: FormEvent) {
    e.preventDefault()
    create.mutate()
  }

  if (warnings && created) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-emerald-700">The request was created.</p>
        {warnings.map((w) => (
          <p key={w} role="alert" className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {w}
          </p>
        ))}
        <div className="flex justify-end">
          <Button onClick={() => finish(created)}>Continue</Button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      {!weddingId && (
        <Select label="Wedding" required value={chosenWedding} onChange={(e) => setChosenWedding(e.target.value)}>
          <option value="">Choose a wedding…</option>
          {weddings.data?.results.map((w) => (
            <option key={w.id} value={w.id}>
              {w.title}
            </option>
          ))}
        </Select>
      )}
      {weddings.error && <p className="text-sm text-red-600">Could not load weddings: {weddings.error.message}</p>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Select
          label="Category"
          required
          value={categoryId}
          error={errors.category_id}
          onChange={(e) => {
            setCategoryId(e.target.value)
            setInvited([])
          }}
        >
          <option value="">Choose…</option>
          {categories?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Input label="Guests" type="number" min={1} value={guests} placeholder="Wedding's guest count" onChange={(e) => setGuests(e.target.value)} error={errors.guest_count} />
        <Input label="Quotes needed by" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} error={errors.due_date} />
      </div>

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">Requirements</span>
        <textarea
          rows={3}
          value={requirements}
          onChange={(e) => setRequirements(e.target.value)}
          placeholder="Menu, timings, counters, anything the vendor should price in"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
      </label>

      <fieldset>
        <legend className="mb-1 text-sm font-medium text-slate-700">Invite vendors</legend>
        {!categoryId && <p className="text-sm text-slate-500">Choose a category to see its vendors.</p>}
        {vendors.isLoading && <p className="text-sm text-slate-500">Loading vendors…</p>}
        {vendors.data && vendors.data.results.length === 0 && (
          <p className="text-sm text-slate-500">No vendors in this category yet. Add some on the Vendors page.</p>
        )}
        <div className="grid max-h-52 gap-1 overflow-y-auto sm:grid-cols-2">
          {vendors.data?.results.map((v) => (
            <label key={v.id} className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">
              <input type="checkbox" checked={invited.includes(v.id)} onChange={() => toggle(v.id)} />
              <span className="flex-1">
                {v.name}
                <span className="block text-xs text-slate-500">
                  {v.city || 'No city'}
                  {v.avg_rating != null && ` · ★ ${v.avg_rating.toFixed(1)}`}
                </span>
              </span>
            </label>
          ))}
        </div>
        {errors.invited_vendor_ids && <p className="mt-1 text-xs text-red-600">{errors.invited_vendor_ids}</p>}
        {fewCaterers && (
          <p role="status" className="mt-2 text-sm text-amber-700">
            We recommend asking at least {CATERER_MINIMUM} caterers so you can compare properly.
          </p>
        )}
      </fieldset>

      {create.error && Object.keys(errors).length === 0 && (
        <p role="alert" className="text-sm text-red-600">
          {create.error.message}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" loading={create.isPending} disabled={!chosenWedding || !categoryId}>
          Create request
        </Button>
      </div>
    </form>
  )
}
