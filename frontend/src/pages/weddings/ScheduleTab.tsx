import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, get, patch, post, remove } from '@/api/client'
import { Button, Card, EmptyState, Input, Modal, Select, Spinner } from '@/components/common'
import { formatDateTime, fromLocalInput, toLocalInput } from '@/helpers/date'
import { useLogin } from '@/login/LoginContext'
import { formatTime, useStaffUsers, type ScheduleItem, type WeddingDetail, type WeddingFunction } from './types'

function ItemForm({ fn, item, onClose }: { fn: WeddingFunction; item: ScheduleItem | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const users = useStaffUsers()
  const [form, setForm] = useState({
    title: item?.title ?? '',
    starts: toLocalInput(item?.starts_at ?? fn.starts_at),
    ends: toLocalInput(item?.ends_at),
    responsible: item?.responsible ? String(item.responsible) : '',
    notes: item?.notes ?? '',
  })
  const [error, setError] = useState('')
  const [warnings, setWarnings] = useState<string[]>([])

  const save = useMutation({
    mutationFn: () => {
      const body = {
        title: form.title,
        starts_at: fromLocalInput(form.starts),
        ends_at: fromLocalInput(form.ends),
        responsible: form.responsible ? Number(form.responsible) : null,
        notes: form.notes,
      }
      return item ? patch<ScheduleItem>(`/schedule/${item.id}/`, body) : post<ScheduleItem>(`/functions/${fn.id}/schedule/`, body)
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: ['schedule', fn.id] })
      queryClient.invalidateQueries({ queryKey: ['wedding-schedule', fn.wedding] })
      // overlap is only a warning: the item is saved, and we tell the planner about the clash
      if (saved.warnings?.length) setWarnings(saved.warnings)
      else onClose()
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save.'),
  })

  return (
    <Modal open title={item ? 'Edit schedule item' : `Add to ${fn.name}`} onClose={onClose}>
      {warnings.length > 0 ? (
        <div className="space-y-3">
          <p className="font-medium text-amber-700">Saved, but check these clashes:</p>
          <ul className="list-disc pl-5 text-sm text-amber-800">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
          <div className="flex justify-end">
            <Button onClick={onClose}>OK</Button>
          </div>
        </div>
      ) : (
        <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); setError(''); save.mutate() }}>
          {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}
          <Input label="What happens" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Starts" type="datetime-local" value={form.starts} onChange={(e) => setForm({ ...form, starts: e.target.value })} required />
            <Input label="Ends" type="datetime-local" value={form.ends} onChange={(e) => setForm({ ...form, ends: e.target.value })} required />
          </div>
          <Select label="Responsible" value={form.responsible} onChange={(e) => setForm({ ...form, responsible: e.target.value })}>
            <option value="">Nobody yet</option>
            {users.data?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </Select>
          <Input label="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              Save
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export function ScheduleTab({ wedding }: { wedding: WeddingDetail }) {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [editing, setEditing] = useState<{ fn: WeddingFunction; item: ScheduleItem | null } | null>(null)

  const results = useQueries({
    queries: wedding.functions.map((f) => ({
      queryKey: ['schedule', f.id],
      queryFn: () => get<ScheduleItem[]>(`/functions/${f.id}/schedule/`),
    })),
  })

  const del = useMutation({
    mutationFn: (item: ScheduleItem) => remove(`/schedule/${item.id}/`),
    onSuccess: (_r, item) => {
      queryClient.invalidateQueries({ queryKey: ['schedule', item.function] })
      queryClient.invalidateQueries({ queryKey: ['wedding-schedule', wedding.id] })
    },
  })

  if (wedding.functions.length === 0) return <EmptyState title="Add a function first" hint="Each function has its own run sheet." />

  return (
    <div className="space-y-6">
      <div className="flex justify-end print:hidden">
        <Button variant="secondary" onClick={() => window.print()}>
          Print run sheet
        </Button>
      </div>
      {wedding.functions.map((fn, index) => {
        const result = results[index]
        const items = result?.data ?? []
        return (
          <Card key={fn.id} className="print:break-inside-avoid print:border-0 print:shadow-none">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h3 className="font-semibold">{fn.name}</h3>
                <p className="text-xs text-slate-500">
                  {formatDateTime(fn.starts_at)} → {formatTime(fn.ends_at)} · {fn.venue_name ?? 'No venue'}
                </p>
              </div>
              {canEdit && (
                <Button variant="secondary" className="print:hidden" onClick={() => setEditing({ fn, item: null })}>
                  Add item
                </Button>
              )}
            </div>
            {result?.isLoading && <Spinner />}
            {result?.error && <p className="text-sm text-red-600">{result.error.message}</p>}
            {result?.data && items.length === 0 && <p className="text-sm text-slate-500">No items yet.</p>}
            <ol className="relative ml-2 border-l-2 border-brand-100 pl-5">
              {items.map((item) => (
                <li key={item.id} className="mb-4 last:mb-0">
                  <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full bg-brand-500" />
                  <div className="flex flex-wrap items-baseline gap-x-3">
                    <span className="font-mono text-sm font-semibold text-brand-700">
                      {formatTime(item.starts_at)} – {formatTime(item.ends_at)}
                    </span>
                    <span className="font-medium">{item.title}</span>
                  </div>
                  <div className="text-xs text-slate-500">
                    {item.responsible_name ? `Responsible: ${item.responsible_name}` : 'No one responsible'}
                    {item.vendor_name ? ` · Vendor: ${item.vendor_name}` : ''}
                    {item.notes ? ` · ${item.notes}` : ''}
                  </div>
                  {canEdit && (
                    <div className="mt-1 flex gap-3 text-xs print:hidden">
                      <button className="text-brand-700 hover:underline" onClick={() => setEditing({ fn, item })}>
                        Edit
                      </button>
                      <button
                        className="text-red-600 hover:underline"
                        onClick={() => window.confirm(`Delete “${item.title}”?`) && del.mutate(item)}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </Card>
        )
      })}
      {editing && <ItemForm fn={editing.fn} item={editing.item} onClose={() => setEditing(null)} />}
    </div>
  )
}
