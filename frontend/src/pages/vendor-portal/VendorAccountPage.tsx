import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { ApiError, get, patch, post } from '@/api/client'
import { Button, Card, CardTitle, Input, Spinner } from '@/components/common'
import type { VendorMe } from './types'

export default function VendorAccountPage() {
  const queryClient = useQueryClient()
  const { data } = useQuery({ queryKey: ['vendor-me'], queryFn: () => get<VendorMe>('/portal/vendor/me/') })
  const [form, setForm] = useState<{ contact_person: string; phone: string; city: string; notes: string } | null>(null)
  const [pw, setPw] = useState({ current: '', new: '' })
  const [done, setDone] = useState('')
  const values = form ?? (data && { contact_person: data.vendor.contact_person, phone: data.vendor.phone, city: data.vendor.city, notes: data.vendor.notes })

  const save = useMutation({
    mutationFn: () => patch('/portal/vendor/me/', values),
    onSuccess: () => {
      setDone('Details saved.')
      queryClient.invalidateQueries({ queryKey: ['vendor-me'] })
    },
  })
  const change = useMutation({
    mutationFn: () => post('/portal/vendor/password/', pw),
    onSuccess: () => {
      setDone('Password changed.')
      setPw({ current: '', new: '' })
    },
  })
  if (!data || !values) return <Spinner />
  const set = (key: keyof typeof values) => (e: { target: { value: string } }) => setForm({ ...values, [key]: e.target.value })
  const pwErrors = change.error instanceof ApiError ? change.error.fields : {}

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardTitle>Your details</CardTitle>
        <p className="mb-3 text-sm text-slate-500">{data.vendor.name} · {data.vendor.email}. To change the business name or email, ask our team.</p>
        <form className="space-y-3" onSubmit={(e: FormEvent) => { e.preventDefault(); setDone(''); save.mutate() }}>
          <Input label="Contact person" value={values.contact_person} onChange={set('contact_person')} />
          <Input label="Phone" value={values.phone} onChange={set('phone')} error={save.error instanceof ApiError ? save.error.fields.phone : undefined} />
          <Input label="City" value={values.city} onChange={set('city')} />
          <Input label="About your service" value={values.notes} onChange={set('notes')} />
          <Button type="submit" loading={save.isPending}>Save details</Button>
        </form>
        {data.rating !== null && <p className="mt-4 text-sm text-slate-600">Your average rating from our planners: <b>{data.rating} / 5</b> ({data.ratings_count} ratings)</p>}
      </Card>
      <Card>
        <CardTitle>Change password</CardTitle>
        <form className="space-y-3" onSubmit={(e: FormEvent) => { e.preventDefault(); setDone(''); change.mutate() }}>
          <Input label="Current password" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} error={pwErrors.current} />
          <Input label="New password" type="password" autoComplete="new-password" value={pw.new} onChange={(e) => setPw({ ...pw, new: e.target.value })} error={pwErrors.new} />
          <Button type="submit" loading={change.isPending}>Change password</Button>
        </form>
      </Card>
      {done && <p role="status" className="text-sm text-emerald-600 lg:col-span-2">{done}</p>}
    </div>
  )
}
