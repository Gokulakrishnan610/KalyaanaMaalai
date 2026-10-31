import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { Button, Input, Modal, Select } from '@/components/common'
import { ApiError, patch, post, remove } from '@/api/client'
import { fromLocalInput, toLocalInput } from '@/helpers/date'
import { paiseToRupees, rupeesToPaise } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { SOURCES, STATUSES, type Enquiry } from './types'

const schema = z.object({
  couple_name: z.string().min(1, 'Enter the couple’s name'),
  phone: z.string().regex(/^\d{10}$/, 'Enter a 10-digit phone number'),
  email: z.string().email('Enter a valid email').or(z.literal('')),
  source: z.string().min(1),
  status: z.string(),
  wedding_date: z.string(),
  guest_count: z.string().refine((v) => v === '' || Number(v) >= 1, 'At least 1 guest'),
  budget: z.string().refine((v) => v === '' || Number(v.replace(/,/g, '')) >= 0, 'Enter a valid amount'),
  venue_city: z.string(),
  consultation_at: z.string(),
  notes: z.string(),
})
type FormValues = z.infer<typeof schema>

interface Props {
  /** an existing enquiry to edit, or null to add a new one */
  enquiry: Enquiry | null
  onClose: () => void
}

export function EnquiryForm({ enquiry, onClose }: Props) {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [message, setMessage] = useState('')
  const [alsoCreateWedding, setAlsoCreateWedding] = useState(false)
  const [convertedTo, setConvertedTo] = useState<number | null>(enquiry?.client ?? null)

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      couple_name: enquiry?.couple_name ?? '',
      phone: enquiry?.phone ?? '',
      email: enquiry?.email ?? '',
      source: enquiry?.source ?? 'CALL',
      status: enquiry?.status ?? 'NEW',
      wedding_date: enquiry?.wedding_date ?? '',
      guest_count: enquiry?.guest_count?.toString() ?? '',
      budget: enquiry?.budget_paise ? String(paiseToRupees(enquiry.budget_paise)) : '',
      venue_city: enquiry?.venue_city ?? '',
      consultation_at: toLocalInput(enquiry?.consultation_at),
      notes: enquiry?.notes ?? '',
    },
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['enquiries'] })

  const save = useMutation({
    mutationFn: (v: FormValues) => {
      const body = {
        couple_name: v.couple_name,
        phone: v.phone,
        email: v.email,
        source: v.source,
        status: v.status,
        wedding_date: v.wedding_date || null,
        guest_count: v.guest_count ? Number(v.guest_count) : null,
        budget_paise: v.budget ? rupeesToPaise(v.budget) : null,
        venue_city: v.venue_city,
        consultation_at: fromLocalInput(v.consultation_at),
        notes: v.notes,
      }
      return enquiry ? patch<Enquiry>(`/enquiries/${enquiry.id}/`, body) : post<Enquiry>('/enquiries/', body)
    },
    onSuccess: () => {
      refresh()
      onClose()
    },
    onError: (e) => {
      if (!(e instanceof ApiError)) return setMessage('Could not reach the server')
      setMessage(e.message)
      const names: Record<string, keyof FormValues> = { budget_paise: 'budget' }
      for (const [field, text] of Object.entries(e.fields)) {
        const name = names[field] ?? (field as keyof FormValues)
        if (name in schema.shape) setError(name, { message: text })
      }
    },
  })

  const convert = useMutation({
    mutationFn: () =>
      post<{ client: { id: number }; wedding_id: number | null }>(`/enquiries/${enquiry!.id}/convert/`, {
        create_wedding: alsoCreateWedding,
      }),
    onSuccess: (res) => {
      refresh()
      setConvertedTo(res.client.id)
      setValue('status', 'WON') // keep the form in step, so Save does not undo the conversion
      setMessage(res.wedding_id ? 'Client and wedding created.' : 'Client created.')
    },
    onError: (e) => setMessage(e instanceof ApiError ? e.message : 'Could not reach the server'),
  })

  const destroy = useMutation({
    mutationFn: () => remove(`/enquiries/${enquiry!.id}/`),
    onSuccess: () => {
      refresh()
      onClose()
    },
  })

  return (
    <Modal open title={enquiry ? enquiry.couple_name : 'New enquiry'} onClose={onClose} wide>
      <form onSubmit={handleSubmit((v) => save.mutate(v))} noValidate className="space-y-4">
        <fieldset disabled={!canEdit} className="grid gap-4 sm:grid-cols-2">
          <Input label="Couple" error={errors.couple_name?.message} {...register('couple_name')} />
          <Input label="Phone" inputMode="numeric" maxLength={10} error={errors.phone?.message} {...register('phone')} />
          <Input label="Email" type="email" error={errors.email?.message} {...register('email')} />
          <Select label="How did they reach us?" {...register('source')}>
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.icon} {s.label}
              </option>
            ))}
          </Select>
          <Input label="Wedding date" type="date" error={errors.wedding_date?.message} {...register('wedding_date')} />
          <Input label="Guests" type="number" min={1} error={errors.guest_count?.message} {...register('guest_count')} />
          <Input label="Budget (₹)" inputMode="decimal" error={errors.budget?.message} {...register('budget')} />
          <Input label="City" {...register('venue_city')} />
          <Input label="First consultation meeting" type="datetime-local" {...register('consultation_at')} />
          {enquiry && (
            <Select label="Stage" {...register('status')}>
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          )}
          <label className="block text-sm sm:col-span-2">
            <span className="mb-1 block font-medium text-slate-700">Notes</span>
            <textarea
              rows={3}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              {...register('notes')}
            />
          </label>
        </fieldset>

        {message && (
          <p role="status" className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700">
            {message}
          </p>
        )}

        {enquiry && (
          <div className="rounded-lg border border-slate-200 p-3 text-sm">
            {convertedTo ? (
              <span>
                This couple is already a client.{' '}
                <Link className="font-medium text-brand-600 underline" to={`/clients/${convertedTo}`} onClick={onClose}>
                  Open client profile
                </Link>
              </span>
            ) : (
              canEdit && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={alsoCreateWedding} onChange={(e) => setAlsoCreateWedding(e.target.checked)} />
                    Also start the wedding project
                  </label>
                  <Button type="button" variant="secondary" loading={convert.isPending} onClick={() => convert.mutate()}>
                    Convert to client
                  </Button>
                </div>
              )
            )}
          </div>
        )}

        <div className="flex justify-between">
          <div>
            {enquiry && hasRole() && (
              <Button
                type="button"
                variant="danger"
                loading={destroy.isPending}
                onClick={() => window.confirm('Delete this enquiry?') && destroy.mutate()}
              >
                Delete
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              {canEdit ? 'Cancel' : 'Close'}
            </Button>
            {canEdit && (
              <Button type="submit" loading={save.isPending}>
                {enquiry ? 'Save changes' : 'Add enquiry'}
              </Button>
            )}
          </div>
        </div>
      </form>
    </Modal>
  )
}
