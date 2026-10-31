import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError, get, patch, post, remove } from '@/api/client'
import { Button, Card, CardTitle, EmptyState, Input, Modal, Select } from '@/components/common'
import { formatDateTime, fromLocalInput, toLocalInput } from '@/helpers/date'
import { useLogin } from '@/login/LoginContext'
import { ROLE_LABELS, useStaffUsers, type WeddingDetail, type WeddingFunction } from './types'

interface Venue {
  id: number
  name: string
  city: string
}

function FunctionForm({ weddingId, fn, onClose }: { weddingId: number; fn: WeddingFunction | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const venues = useQuery({ queryKey: ['venues'], queryFn: () => get<Venue[]>('/venues/') })
  const [name, setName] = useState(fn?.name ?? '')
  const [starts, setStarts] = useState(toLocalInput(fn?.starts_at))
  const [ends, setEnds] = useState(toLocalInput(fn?.ends_at))
  const [venue, setVenue] = useState(fn?.venue ? String(fn.venue) : '')
  const [guests, setGuests] = useState(fn?.guest_count ? String(fn.guest_count) : '')
  const [newVenue, setNewVenue] = useState('')
  const [error, setError] = useState('')

  const save = useMutation({
    mutationFn: async () => {
      let venueId = venue ? Number(venue) : null
      if (newVenue.trim()) venueId = (await post<Venue>('/venues/', { name: newVenue.trim() })).id
      const body = {
        name,
        starts_at: fromLocalInput(starts),
        ends_at: fromLocalInput(ends),
        venue: venueId,
        guest_count: guests ? Number(guests) : null,
      }
      return fn ? patch(`/functions/${fn.id}/`, body) : post(`/weddings/${weddingId}/functions/`, body)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wedding', weddingId] })
      queryClient.invalidateQueries({ queryKey: ['venues'] })
      onClose()
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save the function.'),
  })

  return (
    <Modal open title={fn ? 'Edit function' : 'Add function'} onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          setError('')
          save.mutate()
        }}
      >
        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
        <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Starts" type="datetime-local" value={starts} onChange={(e) => setStarts(e.target.value)} required />
          <Input label="Ends" type="datetime-local" value={ends} onChange={(e) => setEnds(e.target.value)} required />
        </div>
        <Select label="Venue" value={venue} onChange={(e) => setVenue(e.target.value)}>
          <option value="">No venue yet</option>
          {venues.data?.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
              {v.city ? `, ${v.city}` : ''}
            </option>
          ))}
        </Select>
        <Input label="…or add a new venue" value={newVenue} onChange={(e) => setNewVenue(e.target.value)} />
        <Input label="Guests (optional)" type="number" min={1} value={guests} onChange={(e) => setGuests(e.target.value)} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending}>
            Save
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function TeamEditor({ wedding }: { wedding: WeddingDetail }) {
  const queryClient = useQueryClient()
  const users = useStaffUsers()
  const [rows, setRows] = useState(wedding.assignments.map((a) => ({ user_id: a.user_id, role_label: a.role_label })))
  const [error, setError] = useState('')
  const save = useMutation({
    mutationFn: async () => (await api.put(`/weddings/${wedding.id}/assignments/`, rows)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wedding', wedding.id] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save the team.'),
  })
  return (
    <Card>
      <CardTitle>Team and roles</CardTitle>
      {error && <p className="mb-2 text-sm text-red-600" role="alert">{error}</p>}
      <div className="space-y-2">
        {rows.map((row, index) => (
          <div key={index} className="flex flex-wrap gap-2">
            <Select aria-label="Person" value={row.user_id} onChange={(e) => setRows(rows.map((r, i) => (i === index ? { ...r, user_id: Number(e.target.value) } : r)))}>
              {users.data?.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </Select>
            <Select aria-label="Role" value={row.role_label} onChange={(e) => setRows(rows.map((r, i) => (i === index ? { ...r, role_label: e.target.value } : r)))}>
              {Object.entries(ROLE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Button variant="ghost" onClick={() => setRows(rows.filter((_, i) => i !== index))}>
              Remove
            </Button>
          </div>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <Button
          variant="secondary"
          disabled={!users.data?.length}
          onClick={() => users.data && setRows([...rows, { user_id: users.data[0].id, role_label: 'COORDINATOR' }])}
        >
          Add person
        </Button>
        <Button loading={save.isPending} onClick={() => { setError(''); save.mutate() }}>
          Save team
        </Button>
      </div>
    </Card>
  )
}

export function FunctionsTab({ wedding }: { wedding: WeddingDetail }) {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [editing, setEditing] = useState<WeddingFunction | 'new' | null>(null)

  const del = useMutation({
    mutationFn: (id: number) => remove(`/functions/${id}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wedding', wedding.id] }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Functions</h2>
        {canEdit && <Button onClick={() => setEditing('new')}>Add function</Button>}
      </div>
      {wedding.functions.length === 0 ? (
        <EmptyState title="No functions yet" hint="Add Mehendi, Sangeet, Wedding, Reception…" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {wedding.functions.map((fn) => (
            <Card key={fn.id}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold">{fn.name}</div>
                  <div className="text-sm text-slate-600">
                    {formatDateTime(fn.starts_at)} → {formatDateTime(fn.ends_at)}
                  </div>
                  <div className="text-sm text-slate-500">
                    {fn.venue_name ?? 'No venue'}
                    {fn.guest_count ? ` · ${fn.guest_count} guests` : ''}
                  </div>
                </div>
                {canEdit && (
                  <div className="flex gap-1">
                    <Button variant="ghost" onClick={() => setEditing(fn)}>
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => window.confirm(`Delete ${fn.name}?`) && del.mutate(fn.id)}
                    >
                      Delete
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
      {canEdit && <TeamEditor key={JSON.stringify(wedding.assignments)} wedding={wedding} />}
      {editing && (
        <FunctionForm weddingId={wedding.id} fn={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />
      )}
    </div>
  )
}
