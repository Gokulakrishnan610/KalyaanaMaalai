import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { useState } from 'react'
import { Button, cn, Select } from '@/components/common'
import { ApiError, get, post } from '@/api/client'
import { formatDateTime, fromLocalInput } from '@/helpers/date'
import { FOLLOW_UP_KINDS, type FollowUp } from './types'

/** Planned calls and meetings for one enquiry: list them, add one, tick them off. */
export function FollowUps({ enquiryId, canEdit }: { enquiryId: number; canEdit: boolean }) {
  const queryClient = useQueryClient()
  const key = ['follow-ups', enquiryId]
  const { data = [] } = useQuery({ queryKey: key, queryFn: () => get<FollowUp[]>('/follow-ups/', { enquiry: enquiryId }) })

  const [kind, setKind] = useState('CALL')
  const [summary, setSummary] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [message, setMessage] = useState('')

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: key })
    queryClient.invalidateQueries({ queryKey: ['enquiries'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
  }

  const add = useMutation({
    mutationFn: () => post('/follow-ups/', { enquiry: enquiryId, kind, summary, due_at: fromLocalInput(dueAt) }),
    onSuccess: () => {
      setSummary('')
      setDueAt('')
      setMessage('')
      refresh()
    },
    onError: (e) => setMessage(e instanceof ApiError ? e.message : 'Could not reach the server'),
  })
  const finish = useMutation({ mutationFn: (id: number) => post(`/follow-ups/${id}/done/`), onSuccess: refresh })

  return (
    <div className="rounded-xl border border-slate-200 p-3">
      <div className="mb-2 text-sm font-semibold text-slate-700">Follow-ups</div>
      {data.length === 0 && <p className="mb-2 text-sm text-slate-500">Nothing planned yet.</p>}
      <ul className="mb-3 space-y-1.5">
        {data.map((f) => {
          const info = FOLLOW_UP_KINDS.find((k) => k.value === f.kind)!
          return (
            <li key={f.id} className="flex items-center gap-2 text-sm">
              <button
                type="button"
                disabled={!canEdit || !!f.done_at}
                aria-label={f.done_at ? 'Done' : 'Mark as done'}
                onClick={() => finish.mutate(f.id)}
                className={cn(
                  'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                  f.done_at ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-300 hover:border-brand-500',
                )}
              >
                {f.done_at && <Check size={12} />}
              </button>
              <span className={cn('flex-1', f.done_at && 'text-slate-400 line-through')}>
                {info.icon} {f.summary}
              </span>
              <span className={cn('text-xs', f.is_overdue ? 'font-medium text-red-600' : 'text-slate-500')}>
                {f.is_overdue && 'Overdue · '}
                {formatDateTime(f.due_at)}
              </span>
            </li>
          )
        })}
      </ul>
      {canEdit && (
        <div className="grid gap-2 sm:grid-cols-[8rem_1fr_11rem_auto]">
          <Select aria-label="Type" value={kind} onChange={(e) => setKind(e.target.value)}>
            {FOLLOW_UP_KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.icon} {k.label}
              </option>
            ))}
          </Select>
          <input
            aria-label="What to do"
            placeholder="e.g. Call about the venue"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <input
            aria-label="When"
            type="datetime-local"
            value={dueAt}
            onChange={(e) => setDueAt(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <Button type="button" variant="secondary" disabled={!summary || !dueAt} loading={add.isPending} onClick={() => add.mutate()}>
            Add
          </Button>
        </div>
      )}
      {message && <p className="mt-2 text-sm text-red-600">{message}</p>}
    </div>
  )
}
