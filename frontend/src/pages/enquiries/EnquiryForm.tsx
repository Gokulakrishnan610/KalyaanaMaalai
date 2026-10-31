import { zodResolver } from '@hookform/resolvers/zod'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { Button, Input, Modal, Select } from '@/components/common'
import { ApiError, get, patch, post, remove } from '@/api/client'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { fromLocalInput, toLocalInput } from '@/helpers/date'
import { paiseToRupees, rupeesToPaise } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { FollowUps } from './FollowUps'
import { StarRating } from './StarRating'
import { CONTACT_LABELS, LOST_REASONS, SOURCES, STAGE_WIN_CHANCE, STATUSES, WEBSITE_FUNCTIONS, WEBSITE_SERVICES, type Enquiry, type Status } from './types'

const schema = z.object({
  client_name: z.string(),
  partner_name: z.string(),
  spouse_email: z.string().email('Enter a valid email').or(z.literal('')),
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
  expected_fee: z.string().refine((v) => v === '' || Number(v.replace(/,/g, '')) >= 0, 'Enter a valid amount'),
  win_chance: z.string().refine((v) => v !== '' && Number(v) >= 0 && Number(v) <= 100, 'Enter 0 to 100'),
  priority: z.string(),
  expected_close_date: z.string(),
  lost_reason: z.string(),
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
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      client_name: enquiry?.client_name ?? '',
      partner_name: enquiry?.partner_name ?? '',
      spouse_email: enquiry?.spouse_email ?? '',
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
      expected_fee: enquiry?.expected_revenue_paise ? String(paiseToRupees(enquiry.expected_revenue_paise)) : '',
      win_chance: String(enquiry?.win_chance ?? STAGE_WIN_CHANCE.NEW),
      priority: String(enquiry?.priority ?? 0),
      expected_close_date: enquiry?.expected_close_date ?? '',
      lost_reason: enquiry?.lost_reason ?? '',
    },
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['enquiries'] })

  // a client is recognised by client name + email: say so when this person is already one of ours
  const typedName = useDebouncedValue(watch('client_name').trim(), 400)
  const typedEmail = useDebouncedValue(watch('email').trim(), 400)
  const knownClient = useQuery({
    queryKey: ['client-lookup', typedName, typedEmail],
    queryFn: ({ signal }) =>
      get<{ client: { id: number; couple_name: string; spouse_name: string } | null }>(
        '/clients/lookup/',
        { client_name: typedName, email: typedEmail },
        signal,
      ),
    enabled: !enquiry?.client && typedName !== '' && /\S+@\S+\.\S+/.test(typedEmail),
    placeholderData: keepPreviousData,
  })
  const existingClient = knownClient.data?.client

  const save = useMutation({
    mutationFn: (v: FormValues) => {
      if (!v.client_name.trim() && !enquiry?.couple_name) throw new ApiError(400, 'Enter the client’s name', { client_name: 'Enter the client’s name' })
      const clientName = v.client_name.trim()
      const spouse = v.partner_name.trim()
      const body = {
        client_name: clientName,
        partner_name: spouse,
        spouse_email: v.spouse_email,
        // how the couple is shown in lists: "Client & Spouse" (an older enquiry without a client name keeps its own)
        couple_name: clientName ? [clientName, spouse].filter(Boolean).join(' & ') : enquiry?.couple_name ?? '',
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
        expected_revenue_paise: v.expected_fee ? rupeesToPaise(v.expected_fee) : null,
        win_chance: Number(v.win_chance),
        priority: Number(v.priority),
        expected_close_date: v.expected_close_date || null,
        lost_reason: v.status === 'LOST' ? v.lost_reason : '',
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
      const names: Record<string, keyof FormValues> = { budget_paise: 'budget', expected_revenue_paise: 'expected_fee', couple_name: 'client_name' }
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
      setValue('win_chance', '100')
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
          <Input label="Client name" autoComplete="off" error={errors.client_name?.message} {...register('client_name')} />
          <Input label="Client phone number" inputMode="numeric" maxLength={10} error={errors.phone?.message} {...register('phone')} />
          <Input label="Client email ID" type="email" error={errors.email?.message} {...register('email')} />
          <Input label="Spouse name" autoComplete="off" error={errors.partner_name?.message} {...register('partner_name')} />
          <Input label="Spouse email ID" type="email" error={errors.spouse_email?.message} {...register('spouse_email')} />
          {existingClient && (
            <p role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 sm:col-span-2">
              {existingClient.couple_name} is already our client (same name and email). This enquiry will be linked to them,
              and no second client record will be created.
            </p>
          )}
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
          <Input label="Wedding Destination" {...register('venue_city')} />
          <Input label="First consultation meeting" type="datetime-local" {...register('consultation_at')} />
          {enquiry && (
            <Select
              label="Stage"
              {...register('status', {
                // a new stage brings its usual win chance, which can still be edited by hand
                onChange: (e) => setValue('win_chance', String(STAGE_WIN_CHANCE[e.target.value as Status])),
              })}
            >
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          )}
          <Input label="Expected fee for us (₹)" inputMode="decimal" error={errors.expected_fee?.message} {...register('expected_fee')} />
          <Input label="Chance of winning (%)" type="number" min={0} max={100} error={errors.win_chance?.message} {...register('win_chance')} />
          <Input label="Expected decision date" type="date" {...register('expected_close_date')} />
          <div className="text-sm">
            <span className="mb-1 block font-medium text-slate-700">Priority</span>
            <StarRating value={Number(watch('priority'))} onChange={canEdit ? (n) => setValue('priority', String(n)) : undefined} />
          </div>
          {watch('status') === 'LOST' && (
            <Select label="Why was it lost?" error={errors.lost_reason?.message} {...register('lost_reason')}>
              <option value="">Choose a reason…</option>
              {LOST_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
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

        {enquiry && enquiry.source === 'WEBSITE' && (
          <div className="rounded-xl border border-brand-100 bg-brand-50/40 p-3 text-sm">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-semibold text-slate-700">From the customer website</span>
              <span className={enquiry.profile_complete ? 'text-xs font-medium text-emerald-600' : 'text-xs font-medium text-amber-600'}>
                {enquiry.profile_complete ? 'Profile complete' : 'Profile not finished'}
              </span>
            </div>
            <dl className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
              <div><dt className="text-xs text-slate-500">Partner</dt><dd>{enquiry.partner_name || '-'}</dd></div>
              <div><dt className="text-xs text-slate-500">Prefers to be contacted by</dt><dd>{CONTACT_LABELS[enquiry.preferred_contact] ?? '-'}</dd></div>
              <div><dt className="text-xs text-slate-500">Functions wanted</dt><dd>{enquiry.functions_wanted.map((c) => WEBSITE_FUNCTIONS[c] ?? c).join(', ') || '-'}</dd></div>
              <div><dt className="text-xs text-slate-500">Needs help with</dt><dd>{enquiry.services_needed.map((c) => WEBSITE_SERVICES[c] ?? c).join(', ') || '-'}</dd></div>
            </dl>
          </div>
        )}

        {enquiry && <FollowUps enquiryId={enquiry.id} canEdit={canEdit} />}

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
