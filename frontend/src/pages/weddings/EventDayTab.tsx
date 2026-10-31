import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, get, patch, post } from '@/api/client'
import { Badge, Button, Card, CardTitle, EmptyState, ErrorState, Input, Modal, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDateTime, fromLocalInput } from '@/helpers/date'
import { useLogin } from '@/login/LoginContext'
import { formatTime, ROLE_LABELS, type Checkin, type ScheduleItem, type WeddingDetail } from './types'

const STATUS_TONE = { ON_TIME: 'green', LATE: 'red', PENDING: 'gray' } as const
const STATUS_LABEL = { ON_TIME: 'On time', LATE: 'Late', PENDING: 'Pending' } as const

function ResponsibilityMatrix({ wedding }: { wedding: WeddingDetail }) {
  const items = useQuery({
    queryKey: ['wedding-schedule', wedding.id],
    queryFn: () => get<ScheduleItem[]>(`/weddings/${wedding.id}/schedule/`),
  })
  const functionName = (id: number) => wedding.functions.find((f) => f.id === id)?.name ?? ''
  const groups = new Map<string, ScheduleItem[]>()
  for (const item of items.data ?? []) {
    const key = item.responsible_name ?? 'Nobody assigned'
    groups.set(key, [...(groups.get(key) ?? []), item])
  }
  return (
    <Card>
      <CardTitle>Who is responsible for what</CardTitle>
      {items.isLoading && <Spinner />}
      {items.error && <ErrorState message={items.error.message} />}
      {items.data && groups.size === 0 && <p className="text-sm text-slate-500">No schedule items yet.</p>}
      <div className="space-y-4">
        {[...groups].map(([person, rows]) => (
          <div key={person}>
            <div className="mb-1 text-sm font-semibold">{person}</div>
            <ul className="space-y-0.5 text-sm text-slate-600">
              {rows.map((r) => (
                <li key={r.id}>
                  <span className="font-mono text-xs text-brand-700">{formatTime(r.starts_at)}–{formatTime(r.ends_at)}</span>{' '}
                  {r.title} <span className="text-xs text-slate-400">({functionName(r.function)})</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  )
}

function OnDuty({ wedding }: { wedding: WeddingDetail }) {
  return (
    <Card>
      <CardTitle>On duty</CardTitle>
      {wedding.assignments.length === 0 ? (
        <p className="text-sm text-slate-500">No team assigned. Add people on the Functions tab.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {wedding.assignments.map((m) => (
            <li key={m.id} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="font-medium">{m.user_name}</span>
              <span className="text-slate-500">{ROLE_LABELS[m.role_label] ?? m.role_label}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function NewCheckin({ wedding, onClose }: { wedding: WeddingDetail; onClose: () => void }) {
  const queryClient = useQueryClient()
  const vendors = useQuery({
    queryKey: ['vendors', 'options'],
    queryFn: () => get<{ results: { id: number; name: string }[] } | { id: number; name: string }[]>('/vendors/', { page_size: 200 }).catch(() => []),
  })
  const list = Array.isArray(vendors.data) ? vendors.data : (vendors.data?.results ?? [])
  const [vendor, setVendor] = useState('')
  const [fn, setFn] = useState('')
  const [when, setWhen] = useState('')
  const [grace, setGrace] = useState('15')
  const [error, setError] = useState('')
  const save = useMutation({
    mutationFn: () =>
      post(`/weddings/${wedding.id}/checkins/`, {
        vendor_id: Number(vendor),
        function_id: fn ? Number(fn) : null,
        scheduled_arrival: fromLocalInput(when),
        grace_minutes: Number(grace),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['checkins', wedding.id] })
      onClose()
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not create the check-in.'),
  })
  return (
    <Modal open title="New vendor check-in" onClose={onClose}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); setError(''); save.mutate() }}>
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <Select label="Vendor" value={vendor} onChange={(e) => setVendor(e.target.value)} required>
          <option value="">Choose a vendor…</option>
          {list.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </Select>
        <Select label="Function" value={fn} onChange={(e) => setFn(e.target.value)}>
          <option value="">Whole wedding</option>
          {wedding.functions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </Select>
        <Input label="Expected arrival" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} required />
        <Input label="Grace (minutes)" type="number" min={0} value={grace} onChange={(e) => setGrace(e.target.value)} />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function Checkins({ wedding }: { wedding: WeddingDetail }) {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState<number | null>(null)

  // refreshed every 15 seconds, so a vendor tapping "I have arrived" shows up here on its own
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['checkins', wedding.id],
    queryFn: () => get<Checkin[]>(`/weddings/${wedding.id}/checkins/`),
    refetchInterval: 15000,
  })

  const markArrived = useMutation({
    mutationFn: (c: Checkin) => patch(`/checkins/${c.id}/`, { arrived: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['checkins', wedding.id] }),
  })

  const copy = async (c: Checkin) => {
    const link = `${window.location.origin}${c.public_path}`
    try {
      await navigator.clipboard.writeText(link)
    } catch {
      window.prompt('Copy this link', link)
    }
    setCopied(c.id)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <CardTitle className="mb-0">Vendor check-ins</CardTitle>
        <div className="flex items-center gap-3">
          {dataUpdatedAt > 0 && <span className="text-xs text-slate-400">Live · updated {new Date(dataUpdatedAt).toLocaleTimeString('en-IN')}</span>}
          {canEdit && <Button variant="secondary" onClick={() => setCreating(true)}>New check-in</Button>}
        </div>
      </div>
      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && data.length === 0 && <EmptyState title="No check-ins yet" hint="Create one for each vendor and send them their link." />}
      {data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Vendor</Th>
              <Th>Function</Th>
              <Th>Scheduled</Th>
              <Th>Arrived</Th>
              <Th>Delay</Th>
              <Th>Status</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <tr key={c.id}>
                <Td className="font-medium">{c.vendor_name}</Td>
                <Td>{c.function_name ?? '-'}</Td>
                <Td>{formatDateTime(c.scheduled_arrival)}</Td>
                <Td>{formatDateTime(c.actual_arrival)}</Td>
                <Td>{c.delay_minutes == null ? '-' : c.delay_minutes === 0 ? 'On schedule' : `${c.delay_minutes} min`}</Td>
                <Td>
                  <Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge>
                </Td>
                <Td>
                  <div className="flex gap-2">
                    <Button variant="ghost" onClick={() => copy(c)}>
                      {copied === c.id ? 'Copied!' : 'Copy link'}
                    </Button>
                    {canEdit && !c.actual_arrival && (
                      <Button variant="secondary" loading={markArrived.isPending && markArrived.variables?.id === c.id} onClick={() => markArrived.mutate(c)}>
                        Mark arrived
                      </Button>
                    )}
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      {markArrived.error && <p className="mt-2 text-sm text-red-600">{markArrived.error.message}</p>}
      {creating && <NewCheckin wedding={wedding} onClose={() => setCreating(false)} />}
    </Card>
  )
}

export function EventDayTab({ wedding }: { wedding: WeddingDetail }) {
  return (
    <div className="space-y-4">
      <Checkins wedding={wedding} />
      <div className="grid gap-4 lg:grid-cols-3">
        <OnDuty wedding={wedding} />
        <div className="lg:col-span-2">
          <ResponsibilityMatrix wedding={wedding} />
        </div>
      </div>
    </div>
  )
}
