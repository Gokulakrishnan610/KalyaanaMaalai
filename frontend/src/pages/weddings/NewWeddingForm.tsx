import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError, get, post, type Page } from '@/api/client'
import { Button, Input, Modal, Select } from '@/components/common'
import { rupeesToPaise } from '@/helpers/money'
import type { WeddingDetail } from './types'

const schema = z
  .object({
    title: z.string().min(1, 'Enter a title'),
    client_id: z.string().min(1, 'Choose the client'),
    start_date: z.string().min(1, 'Choose the start date'),
    end_date: z.string().min(1, 'Choose the end date'),
    city: z.string().min(1, 'Enter the city'),
    guest_count: z.string().refine((v) => Number(v) >= 1, 'At least 1 guest'),
    contracted_guests: z.string(),
    per_guest_rate: z.string().refine((v) => v === '' || Number(v.replace(/,/g, '')) >= 0, 'Enter a valid amount'),
    budget: z.string().refine((v) => v === '' || Number(v.replace(/,/g, '')) >= 0, 'Enter a valid amount'),
    default_functions: z.boolean(),
  })
  .refine((v) => !v.start_date || !v.end_date || v.end_date >= v.start_date, {
    message: 'The end date cannot be before the start date',
    path: ['end_date'],
  })
type FormValues = z.infer<typeof schema>

interface ClientOption {
  id: number
  couple_name: string
  city: string
}

/** `prefill` comes from the page address (?clientId=&guests=&date=&budget=), e.g. from a converted enquiry. */
export interface Prefill {
  clientId?: string
  guests?: string
  date?: string
  budget?: string
}

export function NewWeddingForm({ prefill, onClose }: { prefill: Prefill; onClose: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('')

  const clients = useQuery({
    queryKey: ['clients', 'options'],
    queryFn: () => get<Page<ClientOption>>('/clients/', { page_size: 200 }),
  })

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: '',
      client_id: prefill.clientId ?? '',
      start_date: prefill.date ?? '',
      end_date: prefill.date ?? '',
      city: '',
      guest_count: prefill.guests ?? '',
      contracted_guests: '',
      per_guest_rate: '',
      budget: prefill.budget && Number(prefill.budget) > 0 ? String(Number(prefill.budget)) : '',
      default_functions: true,
    },
  })

  const save = useMutation({
    mutationFn: (v: FormValues) =>
      post<WeddingDetail>('/weddings/', {
        title: v.title,
        client: Number(v.client_id),
        start_date: v.start_date,
        end_date: v.end_date,
        city: v.city,
        guest_count: Number(v.guest_count),
        contracted_guests: v.contracted_guests ? Number(v.contracted_guests) : undefined,
        per_guest_rate_paise: v.per_guest_rate ? rupeesToPaise(v.per_guest_rate) : 0,
        budget_paise: v.budget ? rupeesToPaise(v.budget) : 0,
        default_functions: v.default_functions,
      }),
    onSuccess: (wedding) => {
      queryClient.invalidateQueries({ queryKey: ['weddings'] })
      navigate(`/weddings/${wedding.id}`)
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        for (const [field, text] of Object.entries(error.fields)) {
          const name = field === 'client' ? 'client_id' : field.replace('_paise', '')
          if (name in schema.shape || name === 'budget' || name === 'per_guest_rate') setError(name as keyof FormValues, { message: text })
        }
        setMessage(error.message)
      } else setMessage('Could not save the wedding. Please try again.')
    },
  })

  // choosing a client suggests a title and city, unless the person already typed them
  const onClientChange = (id: string) => {
    const client = clients.data?.results.find((c) => String(c.id) === id)
    if (client) {
      setValue('title', `${client.couple_name} wedding`, { shouldDirty: false })
      if (client.city) setValue('city', client.city)
    }
  }

  return (
    <Modal open title="New wedding" onClose={onClose} wide>
      <form onSubmit={handleSubmit((v) => save.mutate(v))} className="space-y-4" noValidate>
        {message && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{message}</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Select
            label="Client"
            error={errors.client_id?.message}
            {...register('client_id', { onChange: (e) => onClientChange(e.target.value) })}
          >
            <option value="">Choose a client…</option>
            {clients.data?.results.map((c) => (
              <option key={c.id} value={c.id}>
                {c.couple_name}
              </option>
            ))}
          </Select>
          <Input label="Title" error={errors.title?.message} {...register('title')} />
          <Input label="Start date" type="date" error={errors.start_date?.message} {...register('start_date')} />
          <Input label="End date" type="date" error={errors.end_date?.message} {...register('end_date')} />
          <Input label="City" error={errors.city?.message} {...register('city')} />
          <Input label="Guests" type="number" min={1} error={errors.guest_count?.message} {...register('guest_count')} />
          <Input
            label="Contracted guests (optional)"
            type="number"
            min={1}
            placeholder="Same as guests"
            error={errors.contracted_guests?.message}
            {...register('contracted_guests')}
          />
          <Input label="Rate per extra guest (₹)" inputMode="decimal" error={errors.per_guest_rate?.message} {...register('per_guest_rate')} />
          <Input label="Budget (₹)" inputMode="decimal" error={errors.budget?.message} {...register('budget')} />
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('default_functions')} />
          Add Mehendi, Sangeet, Wedding and Reception on consecutive days
        </label>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending}>
            Create wedding
          </Button>
        </div>
      </form>
    </Modal>
  )
}
