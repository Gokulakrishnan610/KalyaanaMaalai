import {
  closestCorners,
  DndContext,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, get, patch, post, remove } from '@/api/client'
import { Badge, Button, cn, ErrorState, Input, Modal, Select, Spinner } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { AIChecklistButton } from '@/pages/ai/AIChecklistPreview'
import { useLogin } from '@/login/LoginContext'
import { initials, STAGES, useStaffUsers, type Priority, type Stage, type Task, type WeddingDetail } from './types'

const PRIORITY_TONE: Record<Priority, 'gray' | 'amber' | 'red'> = { LOW: 'gray', MEDIUM: 'amber', HIGH: 'red' }

/** Returns the list with `id` moved to `stage` at `index` and every column renumbered 0..n (mirrors the server). */
export function applyMove(tasks: Task[], id: number, stage: Stage, index: number): Task[] {
  const moving = tasks.find((t) => t.id === id)
  if (!moving) return tasks
  const columns = Object.fromEntries(
    STAGES.map((s) => [s.value, tasks.filter((t) => t.stage === s.value && t.id !== id).sort((a, b) => a.position - b.position)]),
  ) as Record<Stage, Task[]>
  columns[stage].splice(Math.min(index, columns[stage].length), 0, { ...moving, stage })
  return STAGES.flatMap((s) => columns[s.value].map((t, position) => ({ ...t, position })))
}

function Card({ task, onOpen, canEdit }: { task: Task; onOpen: (t: Task) => void; canEdit: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: String(task.id),
    disabled: !canEdit,
  })
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={() => onOpen(task)}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'cursor-pointer rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm hover:border-brand-500',
        isDragging && 'z-10 opacity-70 shadow-lg',
      )}
    >
      <div className="font-medium">{task.title}</div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <Badge tone={PRIORITY_TONE[task.priority]}>{task.priority.toLowerCase()}</Badge>
        {task.function_name && <Badge tone="blue">{task.function_name}</Badge>}
      </div>
      <div className="mt-2 flex items-center justify-between text-xs">
        <span className={task.is_overdue ? 'font-medium text-red-600' : 'text-slate-500'}>
          {task.due_date ? `${task.is_overdue ? 'Overdue · ' : ''}${formatDate(task.due_date)}` : 'No due date'}
        </span>
        <span
          title={task.assignee_name ?? 'Unassigned'}
          className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-[10px] font-semibold text-brand-700"
        >
          {task.assignee_name ? initials(task.assignee_name) : '–'}
        </span>
      </div>
    </div>
  )
}

function Column({
  stage,
  label,
  tasks,
  visibleIds,
  canEdit,
  onOpen,
  onAdd,
}: {
  stage: Stage
  label: string
  tasks: Task[]
  visibleIds: Set<number>
  canEdit: boolean
  onOpen: (t: Task) => void
  onAdd: (stage: Stage, title: string) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: `col:${stage}` })
  const [title, setTitle] = useState('')
  const shown = tasks.filter((t) => visibleIds.has(t.id))
  return (
    <div ref={setNodeRef} className={cn('w-72 shrink-0 rounded-xl bg-slate-100 p-3', isOver && 'ring-2 ring-brand-500')}>
      <div className="mb-3 flex items-center justify-between text-sm font-semibold text-slate-700">
        {label}
        <span className="rounded-full bg-white px-2 text-xs font-medium text-slate-500">{tasks.length}</span>
      </div>
      <SortableContext items={shown.map((t) => String(t.id))} strategy={verticalListSortingStrategy}>
        <div className="min-h-16 space-y-2">
          {shown.map((t) => (
            <Card key={t.id} task={t} onOpen={onOpen} canEdit={canEdit} />
          ))}
        </div>
      </SortableContext>
      {canEdit && (
        <form
          className="mt-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (title.trim()) onAdd(stage, title.trim())
            setTitle('')
          }}
        >
          <input
            aria-label={`Quick add to ${label}`}
            placeholder="+ Add a task"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-transparent bg-white/60 px-2 py-1.5 text-sm outline-none focus:border-brand-500 focus:bg-white"
          />
        </form>
      )}
    </div>
  )
}

function TaskDrawer({ task, weddingId, onClose }: { task: Task; weddingId: number; onClose: () => void }) {
  const queryClient = useQueryClient()
  const users = useStaffUsers()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [form, setForm] = useState({
    title: task.title,
    description: task.description,
    assigned_to: task.assigned_to ? String(task.assigned_to) : '',
    due_date: task.due_date ?? '',
    priority: task.priority,
  })
  const [error, setError] = useState('')
  const done = () => {
    queryClient.invalidateQueries({ queryKey: ['tasks', weddingId] })
    queryClient.invalidateQueries({ queryKey: ['wedding-progress', weddingId] })
    queryClient.invalidateQueries({ queryKey: ['wedding', weddingId] })
    onClose()
  }
  const save = useMutation({
    mutationFn: () =>
      patch(`/tasks/${task.id}/`, {
        title: form.title,
        description: form.description,
        assigned_to: form.assigned_to ? Number(form.assigned_to) : null,
        due_date: form.due_date || null,
        priority: form.priority,
      }),
    onSuccess: done,
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save.'),
  })
  const del = useMutation({ mutationFn: () => remove(`/tasks/${task.id}/`), onSuccess: done })

  return (
    <Modal open title="Task" onClose={onClose}>
      <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); setError(''); save.mutate() }}>
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        <Input label="Title" value={form.title} disabled={!canEdit} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Description</span>
          <textarea
            rows={4}
            disabled={!canEdit}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-3">
          <Select label="Assignee" disabled={!canEdit} value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })}>
            <option value="">Unassigned</option>
            {users.data?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </Select>
          <Input label="Due date" type="date" disabled={!canEdit} value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
          <Select label="Priority" disabled={!canEdit} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value as Priority })}>
            <option value="LOW">Low</option>
            <option value="MEDIUM">Medium</option>
            <option value="HIGH">High</option>
          </Select>
        </div>
        {canEdit && (
          <div className="flex justify-between">
            <Button type="button" variant="danger" loading={del.isPending} onClick={() => window.confirm('Delete this task?') && del.mutate()}>
              Delete
            </Button>
            <Button type="submit" loading={save.isPending}>
              Save
            </Button>
          </div>
        )}
      </form>
    </Modal>
  )
}

interface Preview {
  count: number
  tasks: { title: string; due_date: string; assigned_to: number | null; priority: Priority }[]
}

function TemplateDialog({ weddingId, onClose, onDone }: { weddingId: number; onClose: () => void; onDone: (msg: string) => void }) {
  const users = useStaffUsers()
  const preview = useQuery({
    queryKey: ['template-preview', weddingId],
    queryFn: () => post<Preview>(`/weddings/${weddingId}/tasks/from-template/?dry_run=true`, {}),
    gcTime: 0,
  })
  const create = useMutation({
    mutationFn: () => post<Preview>(`/weddings/${weddingId}/tasks/from-template/`, {}),
    onSuccess: (res) => onDone(`Added ${res.count} task${res.count === 1 ? '' : 's'} from the template.`),
  })
  const name = (id: number | null) => users.data?.find((u) => u.id === id)?.name ?? 'Unassigned'
  return (
    <Modal open title="Generate tasks from template" onClose={onClose} wide>
      {preview.isLoading && <Spinner />}
      {preview.error && <ErrorState message={preview.error.message} />}
      {create.error && <ErrorState message={create.error.message} />}
      {preview.data && preview.data.count === 0 && <p className="text-sm text-slate-600">Every template task already exists. Nothing to add.</p>}
      {preview.data && preview.data.count > 0 && (
        <>
          <p className="mb-2 text-sm text-slate-600">{preview.data.count} missing tasks will be added. Existing ones are left alone.</p>
          <div className="max-h-80 overflow-y-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <tbody>
                {preview.data.tasks.map((t) => (
                  <tr key={t.title} className="border-b border-slate-100">
                    <td className="px-3 py-1.5">{t.title}</td>
                    <td className="px-3 py-1.5 text-slate-500">{formatDate(t.due_date)}</td>
                    <td className="px-3 py-1.5 text-slate-500">{name(t.assigned_to)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button loading={create.isPending} disabled={!preview.data || preview.data.count === 0} onClick={() => create.mutate()}>
          Add {preview.data?.count ?? ''} tasks
        </Button>
      </div>
    </Modal>
  )
}

export function TasksTab({ wedding }: { wedding: WeddingDetail }) {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const users = useStaffUsers()
  const [assignee, setAssignee] = useState('')
  const [fn, setFn] = useState('')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [open, setOpen] = useState<Task | null>(null)
  const [templateOpen, setTemplateOpen] = useState(false)
  const [notice, setNotice] = useState<{ ok: boolean; text: string } | null>(null)
  const key = ['tasks', wedding.id]
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: key,
    queryFn: () => get<Task[]>(`/weddings/${wedding.id}/tasks/`),
  })
  const tasks = data ?? []

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: key })
    queryClient.invalidateQueries({ queryKey: ['wedding-progress', wedding.id] })
    queryClient.invalidateQueries({ queryKey: ['wedding', wedding.id] })
    queryClient.invalidateQueries({ queryKey: ['weddings'] })
  }

  // the card jumps at once; if the server refuses, it jumps back
  const move = useMutation({
    mutationFn: ({ id, stage, position }: { id: number; stage: Stage; position: number }) =>
      patch(`/tasks/${id}/move/`, { stage, position }),
    onMutate: async ({ id, stage, position }) => {
      await queryClient.cancelQueries({ queryKey: key })
      const before = queryClient.getQueryData<Task[]>(key)
      if (before) queryClient.setQueryData<Task[]>(key, applyMove(before, id, stage, position))
      return { before }
    },
    onError: (e, _v, ctx) => {
      if (ctx?.before) queryClient.setQueryData(key, ctx.before)
      setNotice({ ok: false, text: `Could not move the task: ${e.message}` })
    },
    onSettled: refreshAll,
  })

  const add = useMutation({
    mutationFn: ({ stage, title }: { stage: Stage; title: string }) => post(`/weddings/${wedding.id}/tasks/`, { title, stage }),
    onSuccess: refreshAll,
    onError: (e) => setNotice({ ok: false, text: e.message }),
  })

  const visible = new Set(
    tasks
      .filter((t) => (assignee ? String(t.assigned_to) === assignee : true))
      .filter((t) => (fn ? String(t.function) === fn : true))
      .filter((t) => (overdueOnly ? t.is_overdue : true))
      .map((t) => t.id),
  )

  const onDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over) return
    const id = Number(active.id)
    const overId = String(over.id)
    let stage: Stage
    let index: number
    if (overId.startsWith('col:')) {
      stage = overId.slice(4) as Stage
      index = tasks.filter((t) => t.stage === stage && t.id !== id).length
    } else {
      const target = tasks.find((t) => String(t.id) === overId)
      if (!target) return
      stage = target.stage
      index = tasks.filter((t) => t.stage === stage).sort((a, b) => a.position - b.position).findIndex((t) => t.id === target.id)
    }
    const current = tasks.find((t) => t.id === id)
    if (!current || (current.stage === stage && current.position === index)) return
    move.mutate({ id, stage, position: index })
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Select aria-label="Filter by assignee" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          <option value="">Everyone</option>
          {users.data?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </Select>
        <Select aria-label="Filter by function" value={fn} onChange={(e) => setFn(e.target.value)}>
          <option value="">All functions</option>
          {wedding.functions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </Select>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={overdueOnly} onChange={(e) => setOverdueOnly(e.target.checked)} />
          Overdue only
        </label>
        <div className="ml-auto flex gap-2">
          {canEdit && <AIChecklistButton weddingId={wedding.id} onAdded={refreshAll} />}
          {canEdit && (
            <Button variant="secondary" onClick={() => setTemplateOpen(true)}>
              Generate from template
            </Button>
          )}
        </div>
      </div>

      {notice && (
        <p
          role="status"
          className={cn('mb-3 rounded-lg p-3 text-sm', notice.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700')}
          onClick={() => setNotice(null)}
        >
          {notice.text}
        </p>
      )}
      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}

      {data && (
        <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={onDragEnd}>
          <div className="flex gap-4 overflow-x-auto pb-4">
            {STAGES.map((s) => (
              <Column
                key={s.value}
                stage={s.value}
                label={s.label}
                tasks={tasks.filter((t) => t.stage === s.value).sort((a, b) => a.position - b.position)}
                visibleIds={visible}
                canEdit={canEdit}
                onOpen={setOpen}
                onAdd={(stage, title) => add.mutate({ stage, title })}
              />
            ))}
          </div>
        </DndContext>
      )}

      {open && <TaskDrawer key={open.id} task={open} weddingId={wedding.id} onClose={() => setOpen(null)} />}
      {templateOpen && (
        <TemplateDialog
          weddingId={wedding.id}
          onClose={() => setTemplateOpen(false)}
          onDone={(text) => {
            setTemplateOpen(false)
            setNotice({ ok: true, text })
            refreshAll()
          }}
        />
      )}
    </div>
  )
}
