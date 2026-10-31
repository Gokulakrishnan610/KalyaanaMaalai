import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { patch, post, ApiError } from '@/api/client'
import { Button, Input, Modal, Select } from '@/components/common'
import type { Vendor } from './types'
import { useVendorCategories } from './useVendorCategories'

export type SavedVendor = Vendor & { duplicate_warning?: boolean; login?: { email: string; password: string }; login_error?: string }

interface Props {
  open: boolean
  vendor?: Vendor | null
  defaultCategoryId?: number
  onClose: () => void
  onSaved: (vendor: SavedVendor) => void
}

/** Add or edit a vendor. A vendor with the same name and phone is still saved, and the page is told so it can warn. */
export function VendorForm({ open, vendor, defaultCategoryId, onClose, onSaved }: Props) {
  // the inner form is remounted each time the modal opens, so it always starts from the right vendor
  return (
    <Modal open={open} title={vendor ? `Edit ${vendor.name}` : 'Add vendor'} onClose={onClose}>
      <FormBody vendor={vendor} defaultCategoryId={defaultCategoryId} onClose={onClose} onSaved={onSaved} />
    </Modal>
  )
}

function FormBody({ vendor, defaultCategoryId, onClose, onSaved }: Omit<Props, 'open'>) {
  const queryClient = useQueryClient()
  const { data: categories } = useVendorCategories()
  const [values, setValues] = useState({
    name: vendor?.name ?? '',
    category_id: String(vendor?.category_id ?? defaultCategoryId ?? ''),
    contact_person: vendor?.contact_person ?? '',
    phone: vendor?.phone ?? '',
    email: vendor?.email ?? '',
    city: vendor?.city ?? '',
    notes: vendor?.notes ?? '',
  })
  const set = (key: keyof typeof values) => (e: { target: { value: string } }) =>
    setValues((v) => ({ ...v, [key]: e.target.value }))

  const save = useMutation({
    mutationFn: () => {
      const body = { ...values, category_id: Number(values.category_id) }
      return vendor ? patch<SavedVendor>(`/vendors/${vendor.id}/`, body) : post<SavedVendor>('/vendors/', body)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] })
      onSaved(saved)
      onClose()
    },
  })
  const errors = save.error instanceof ApiError ? save.error.fields : {}

  function submit(e: FormEvent) {
    e.preventDefault()
    save.mutate()
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <Input label="Vendor name" required value={values.name} onChange={set('name')} error={errors.name} />
      <Select label="Category" required value={values.category_id} onChange={set('category_id')} error={errors.category_id}>
        <option value="">Choose…</option>
        {categories?.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </Select>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Contact person" value={values.contact_person} onChange={set('contact_person')} error={errors.contact_person} />
        <Input
          label="Phone (10 digits)"
          required
          inputMode="numeric"
          maxLength={10}
          value={values.phone}
          onChange={set('phone')}
          error={errors.phone}
        />
        <Input label="Email" type="email" value={values.email} onChange={set('email')} error={errors.email} />
        <Input label="City" value={values.city} onChange={set('city')} error={errors.city} />
      </div>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">Notes</span>
        <textarea
          rows={3}
          value={values.notes}
          onChange={set('notes')}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
      </label>
      {save.error && Object.keys(errors).length === 0 && (
        <p role="alert" className="text-sm text-red-600">
          {save.error.message}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" loading={save.isPending}>
          {vendor ? 'Save changes' : 'Add vendor'}
        </Button>
      </div>
    </form>
  )
}
