import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, get, post } from '@/api/client'
import { Badge, Button, Modal, Select, Spinner } from '@/components/common'
import { formatDateTime } from '@/helpers/date'
import { useLogin } from '@/login/LoginContext'
import { useStaffUsers } from '@/pages/weddings/types'
import { severityInfo, STATUSES, statusInfo, type IncidentDetail as Detail } from './types'

/** One incident: who is on it, what happened so far, and the buttons to move it along. It updates live. */
export function IncidentDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const queryClient = useQueryClient()
  const { user, hasRole } = useLogin()
  const isPlanner = hasRole('PLANNER')
  const { data: users = [] } = useStaffUsers()
  const [note, setNote] = useState('')
  const [error, setError] = useState('')

  const key = ['incidents', 'detail', id]
  const { data: incident } = useQuery({ queryKey: key, queryFn: () => get<Detail>(`/incidents/${id}/`) })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['incidents'] })
  const fail = (e: unknown) => setError(e instanceof ApiError ? e.message : 'Could not reach the server')
  const assign = useMutation({ mutationFn: (userId: number) => post(`/incidents/${id}/assign/`, { user: userId }), onSuccess: refresh, onError: fail })
  const setStatus = useMutation({ mutationFn: (status: string) => post(`/incidents/${id}/status/`, { status }), onSuccess: refresh, onError: fail })
  const addNote = useMutation({
    mutationFn: () => post(`/incidents/${id}/note/`, { note }),
    onSuccess: () => {
      setNote('')
      refresh()
    },
    onError: fail,
  })

  const canMove = !!incident && (isPlanner || incident.assigned_to === user?.id)

  return (
    <Modal open title={incident?.title ?? 'Incident'} onClose={onClose} wide>
      {!incident ? (
        <Spinner />
      ) : (
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={severityInfo(incident.severity).tone}>{severityInfo(incident.severity).label}</Badge>
            <Badge tone={statusInfo(incident.status).tone}>{statusInfo(incident.status).label}</Badge>
            <span className="text-slate-500">
              {incident.wedding_title} · reported by {incident.reported_by_name || 'someone'} · {formatDateTime(incident.created_at)}
            </span>
          </div>
          {incident.description && <p className="whitespace-pre-wrap text-slate-700">{incident.description}</p>}

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 font-medium text-slate-700">Assigned to</div>
              {isPlanner ? (
                <Select aria-label="Assign to" value={incident.assigned_to ?? ''} onChange={(e) => e.target.value && assign.mutate(Number(e.target.value))}>
                  <option value="">Nobody yet</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </Select>
              ) : (
                <div>{incident.assigned_to_name || 'Nobody yet'}</div>
              )}
            </div>
            {canMove && (
              <div>
                <div className="mb-1 font-medium text-slate-700">Move it along</div>
                <div className="flex flex-wrap gap-2">
                  {STATUSES.filter((s) => s.value !== incident.status && s.value !== 'ASSIGNED').map((s) => (
                    <Button key={s.value} variant={s.value === 'RESOLVED' ? 'primary' : 'secondary'} loading={setStatus.isPending && setStatus.variables === s.value} onClick={() => setStatus.mutate(s.value)}>
                      {s.value === 'RESOLVED' ? 'Mark resolved' : s.value === 'OPEN' ? 'Reopen' : 'Start work'}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div>
            <div className="mb-2 font-medium text-slate-700">History</div>
            <ul className="space-y-2 border-l-2 border-slate-200 pl-4">
              {incident.updates.map((u) => (
                <li key={u.id}>
                  <div>{u.message}</div>
                  <div className="text-xs text-slate-400">
                    {u.author_name || 'System'} · {formatDateTime(u.created_at)}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              setError('')
              if (note.trim()) addNote.mutate()
            }}
          >
            <input
              aria-label="Add a note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add a note for the team…"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
            <Button type="submit" variant="secondary" loading={addNote.isPending} disabled={!note.trim()}>
              Add note
            </Button>
          </form>
          {error && <p role="alert" className="text-red-600">{error}</p>}
        </div>
      )}
    </Modal>
  )
}
