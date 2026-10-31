import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { get, patch, post, type Page } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, Modal, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate, formatDateTime } from '@/helpers/date'
import { useLogin } from '@/login/LoginContext'

interface Certificate {
  signed_by: string
  email: string
  signed_at: string
  ip: string | null
  device: string
  hash: string
  text_unchanged: boolean
  company_signer: string
  company: string
  signature: string
}
interface Agreement {
  id: number
  wedding: number
  wedding_title: string
  client_name: string
  title: string
  body: string
  status: 'DRAFT' | 'SENT' | 'SIGNED' | 'VOID'
  status_label: string
  sent_at: string | null
  signed_at: string | null
  certificate: Certificate | null
}
interface WeddingOption {
  id: number
  title: string
}

const tone = { DRAFT: 'gray', SENT: 'amber', SIGNED: 'green', VOID: 'red' } as const

export default function AgreementsPage() {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [open, setOpen] = useState<Agreement | null>(null)
  const [adding, setAdding] = useState(false)
  const { data, isLoading, error, refetch } = useQuery({ queryKey: ['agreements'], queryFn: () => get<Page<Agreement>>('/agreements/', { page_size: 100 }) })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['agreements'] })

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Agreements</h1>
          <p className="text-sm text-slate-500">Service agreements that couples sign online. A draft is made automatically when an enquiry becomes a wedding.</p>
        </div>
        {canEdit && <Button onClick={() => setAdding(true)}>+ New agreement</Button>}
      </div>
      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && data.results.length === 0 && <EmptyState title="No agreements yet" hint="Convert an enquiry with 'start the wedding project' and a draft appears here." />}
      {data && data.results.length > 0 && (
        <Table>
          <thead><tr><Th>Wedding</Th><Th>Couple</Th><Th>Status</Th><Th>Sent</Th><Th>Signed</Th></tr></thead>
          <tbody>
            {data.results.map((a) => (
              <tr key={a.id} className="cursor-pointer hover:bg-slate-50" onClick={() => setOpen(a)}>
                <Td className="font-medium">{a.wedding_title}</Td>
                <Td>{a.client_name}</Td>
                <Td><Badge tone={tone[a.status]}>{a.status_label}</Badge></Td>
                <Td>{a.sent_at ? formatDate(a.sent_at) : '-'}</Td>
                <Td>{a.signed_at ? formatDate(a.signed_at) : '-'}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      {open && <AgreementModal agreement={open} canEdit={canEdit} onClose={() => setOpen(null)} onChanged={refresh} />}
      {adding && <NewAgreement onClose={() => setAdding(false)} onCreated={(a) => { setAdding(false); refresh(); setOpen(a) }} />}
    </div>
  )
}

function NewAgreement({ onClose, onCreated }: { onClose: () => void; onCreated: (a: Agreement) => void }) {
  const [wedding, setWedding] = useState('')
  const weddings = useQuery({ queryKey: ['weddings', 'options'], queryFn: () => get<Page<WeddingOption>>('/weddings/', { page_size: 200 }) })
  const create = useMutation({ mutationFn: () => post<Agreement>('/agreements/', { wedding: Number(wedding) }), onSuccess: onCreated })
  return (
    <Modal open title="New agreement" onClose={onClose}>
      <p className="mb-3 text-sm text-slate-600">The standard terms are filled in from the wedding. You can edit them before sending.</p>
      <Select label="Wedding" value={wedding} onChange={(e) => setWedding(e.target.value)}>
        <option value="">Choose a wedding</option>
        {weddings.data?.results.map((w) => <option key={w.id} value={w.id}>{w.title}</option>)}
      </Select>
      {create.error && <p className="mt-2 text-sm text-red-600">{create.error.message}</p>}
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button disabled={!wedding} loading={create.isPending} onClick={() => create.mutate()}>Create draft</Button>
      </div>
    </Modal>
  )
}

function AgreementModal({ agreement, canEdit, onClose, onChanged }: { agreement: Agreement; canEdit: boolean; onClose: () => void; onChanged: () => void }) {
  const [body, setBody] = useState(agreement.body)
  const [title, setTitle] = useState(agreement.title)
  const [current, setCurrent] = useState(agreement)
  const draft = current.status === 'DRAFT'
  const run = useMutation({
    mutationFn: async (action: 'save' | 'send' | 'cancel') => {
      if (action === 'save' || action === 'send') await patch(`/agreements/${agreement.id}/`, { title, body }).catch((e) => { if (draft) throw e })
      return action === 'save' ? await get<Agreement>(`/agreements/${agreement.id}/`) : await post<Agreement>(`/agreements/${agreement.id}/${action}/`)
    },
    onSuccess: (a) => {
      setCurrent(a)
      onChanged()
    },
  })
  const cert = current.certificate

  return (
    <Modal open wide title={current.title} onClose={onClose}>
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <Badge tone={tone[current.status]}>{current.status_label}</Badge>
        <span className="text-slate-500">{current.wedding_title} · {current.client_name}</span>
      </div>
      {draft && canEdit ? (
        <div className="space-y-3">
          <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={title} onChange={(e) => setTitle(e.target.value)} aria-label="Title" />
          <textarea className="h-80 w-full rounded-lg border border-slate-300 p-3 font-mono text-xs" value={body} onChange={(e) => setBody(e.target.value)} aria-label="Agreement text" />
        </div>
      ) : (
        <pre className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 font-sans text-sm text-slate-700">{current.body}</pre>
      )}

      {cert && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm">
          <div className="mb-2 font-semibold text-emerald-800">Signed: proof we keep</div>
          <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
            <div><dt className="inline text-slate-500">Signed by: </dt><dd className="inline">{cert.signed_by} ({cert.email})</dd></div>
            <div><dt className="inline text-slate-500">When: </dt><dd className="inline">{formatDateTime(cert.signed_at)}</dd></div>
            <div><dt className="inline text-slate-500">From address: </dt><dd className="inline">{cert.ip ?? '-'}</dd></div>
            <div><dt className="inline text-slate-500">For {cert.company}: </dt><dd className="inline">{cert.company_signer}</dd></div>
            <div className="sm:col-span-2"><dt className="inline text-slate-500">Text fingerprint: </dt><dd className="inline break-all font-mono text-xs">{cert.hash}</dd></div>
            <div><dt className="inline text-slate-500">Text unchanged since signing: </dt><dd className={cert.text_unchanged ? 'inline font-medium text-emerald-700' : 'inline font-medium text-red-600'}>{cert.text_unchanged ? 'Yes' : 'NO, it was changed'}</dd></div>
          </dl>
          <img src={cert.signature} alt="Drawn signature" className="mt-3 h-20 rounded border border-slate-200 bg-white" />
        </div>
      )}
      {run.error && <p className="mt-3 text-sm text-red-600">{run.error.message}</p>}
      {canEdit && (
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          {current.status !== 'SIGNED' && current.status !== 'VOID' && (
            <Button variant="danger" loading={run.isPending && run.variables === 'cancel'} onClick={() => window.confirm('Cancel this agreement?') && run.mutate('cancel')}>Cancel agreement</Button>
          )}
          {draft && <Button variant="secondary" loading={run.isPending && run.variables === 'save'} onClick={() => run.mutate('save')}>Save draft</Button>}
          {(draft || current.status === 'SENT') && (
            <Button loading={run.isPending && run.variables === 'send'} onClick={() => run.mutate('send')}>{draft ? 'Send for signing' : 'Send again'}</Button>
          )}
        </div>
      )}
    </Modal>
  )
}
