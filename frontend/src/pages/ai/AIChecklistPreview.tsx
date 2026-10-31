import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { post } from '@/api/client'
import { Button, Modal, Select, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'

interface PreviewTask {
  title: string
  description: string
  category: string
  due_date: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH'
  function_name: string | null
}

interface Preview {
  source: 'ai' | 'template'
  notice: string
  skipped_duplicates: number
  tasks: PreviewTask[]
}

interface Row extends PreviewTask {
  keep: boolean
}

/**
 * "Suggest tasks with AI": a button for the Tasks tab (Member 2 places it). It opens a preview where the planner can
 * edit titles and priorities, untick what they do not want, and add the rest to the wedding.
 *   <AIChecklistButton weddingId={wedding.id} onAdded={() => refetchTasks()} />
 */
export function AIChecklistButton({ weddingId, onAdded }: { weddingId: number; onAdded?: () => void }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<Row[]>([])
  const [result, setResult] = useState('')

  const generate = useMutation({
    mutationFn: () => post<Preview>('/ai/generate-checklist/', { wedding_id: weddingId }),
    onSuccess: (preview) => {
      setRows(preview.tasks.map((t) => ({ ...t, keep: true })))
      setResult('')
    },
  })
  const confirm = useMutation({
    mutationFn: () =>
      post<{ created: number; skipped: number }>('/ai/generate-checklist/confirm/', {
        wedding_id: weddingId,
        tasks: rows
          .filter((r) => r.keep && r.title.trim())
          .map((r) => ({ title: r.title.trim(), description: r.description, category: r.category, due_date: r.due_date, priority: r.priority, function_name: r.function_name })),
      }),
    onSuccess: (done) => {
      setResult(`Added ${done.created} tasks${done.skipped ? ` (${done.skipped} already existed)` : ''}.`)
      setRows([])
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      onAdded?.()
    },
  })

  const start = () => {
    setOpen(true)
    generate.mutate()
  }
  const close = () => {
    setOpen(false)
    setRows([])
    generate.reset()
    confirm.reset()
  }
  const update = (index: number, change: Partial<Row>) => setRows((all) => all.map((row, i) => (i === index ? { ...row, ...change } : row)))
  const kept = rows.filter((r) => r.keep).length

  return (
    <>
      <Button variant="secondary" onClick={start}>
        Suggest tasks with AI
      </Button>
      <Modal open={open} title="Suggested checklist" onClose={close} wide>
        <div className="space-y-3">
          {generate.isPending && <p className="py-8 text-center text-sm text-slate-500">Writing a checklist for this wedding…</p>}
          {generate.error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{generate.error.message}</p>}
          {generate.data?.notice && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">{generate.data.notice}</p>}
          {result && <p className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{result}</p>}
          {rows.length > 0 && (
            <>
              <p className="text-sm text-slate-600">
                {rows.length} tasks suggested{generate.data?.skipped_duplicates ? ` (${generate.data.skipped_duplicates} left out: already on your board)` : ''}.
                Edit anything, untick what you do not need.
              </p>
              <div className="max-h-[50vh] overflow-y-auto">
                <Table>
                  <thead>
                    <tr>
                      <Th>
                        <input
                          type="checkbox"
                          aria-label="Select all"
                          checked={kept === rows.length}
                          onChange={(e) => setRows((all) => all.map((r) => ({ ...r, keep: e.target.checked })))}
                        />
                      </Th>
                      <Th>Task</Th>
                      <Th>Due</Th>
                      <Th>Priority</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, index) => (
                      <tr key={index} className={row.keep ? '' : 'opacity-50'}>
                        <Td>
                          <input type="checkbox" aria-label={`Keep ${row.title}`} checked={row.keep} onChange={(e) => update(index, { keep: e.target.checked })} />
                        </Td>
                        <Td>
                          <input
                            aria-label="Task title"
                            className="w-full rounded border border-transparent px-1 py-0.5 hover:border-slate-300 focus:border-brand-500 focus:outline-none"
                            value={row.title}
                            onChange={(e) => update(index, { title: e.target.value })}
                          />
                          <div className="px-1 text-xs text-slate-500">
                            {row.category}
                            {row.function_name && ` · ${row.function_name}`}
                          </div>
                        </Td>
                        <Td className="whitespace-nowrap">{formatDate(row.due_date)}</Td>
                        <Td>
                          <Select aria-label="Priority" value={row.priority} onChange={(e) => update(index, { priority: e.target.value as Row['priority'] })}>
                            {(['LOW', 'MEDIUM', 'HIGH'] as const).map((p) => (
                              <option key={p} value={p}>
                                {p.toLowerCase()}
                              </option>
                            ))}
                          </Select>
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </>
          )}
          {confirm.error && <p className="text-sm text-red-600">{confirm.error.message}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={close}>
              {result ? 'Close' : 'Cancel'}
            </Button>
            {rows.length > 0 && (
              <Button loading={confirm.isPending} disabled={kept === 0} onClick={() => confirm.mutate()}>
                Add {kept} selected
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </>
  )
}
