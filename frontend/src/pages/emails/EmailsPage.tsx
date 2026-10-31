import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { get } from '@/api/client'
import { Badge, Card, CardTitle, ErrorState, PageHeader, ShowMore, Spinner, cn } from '@/components/common'
import { formatDateTime } from '@/helpers/date'

interface TemplateRow { name: string; subject: string; when: string }
interface Preview { subject: string; html: string }
interface LogRow { id: number; template: string; to: string; subject: string; status: string; created_at: string }

export default function EmailsPage() {
  const [name, setName] = useState('client_welcome')
  const templates = useQuery({ queryKey: ['mail-templates'], queryFn: () => get<TemplateRow[]>('/mail-templates/') })
  const preview = useQuery({ queryKey: ['mail-preview', name], queryFn: () => get<Preview>(`/mail-templates/${name}/`) })
  const log = useQuery({ queryKey: ['mail-log'], queryFn: () => get<LogRow[]>('/mail-log/'), refetchInterval: 15000 })
  if (templates.isLoading) return <Spinner />
  if (templates.error) return <ErrorState message={templates.error.message} onRetry={templates.refetch} />

  return (
    <div>
      <PageHeader title="Emails" description="Every email the system sends by itself. Pick one to see how it looks, with sample values." />
      <div className="grid gap-5 lg:grid-cols-[18rem_1fr]">
        <div className="space-y-1">
          {templates.data?.map((t) => (
            <button key={t.name} onClick={() => setName(t.name)} className={cn('w-full rounded-lg px-3 py-2 text-left text-sm', name === t.name ? 'bg-brand-50 text-brand-700' : 'hover:bg-slate-100')}>
              <div className="font-medium">{t.name.charAt(0).toUpperCase() + t.name.slice(1).replace(/_/g, ' ')}</div>
              <div className="text-xs text-slate-500">{t.when}</div>
            </button>
          ))}
        </div>
        <Card>
          <div className="mb-3 text-sm"><span className="text-slate-500">Subject: </span><b>{preview.data?.subject}</b></div>
          {preview.data && <iframe title="Email preview" sandbox="allow-same-origin" srcDoc={preview.data.html} className="h-[28rem] w-full rounded-lg border border-slate-200 bg-white" />}
        </Card>
      </div>
      <Card className="mt-5">
        <CardTitle>Recently sent</CardTitle>
        {log.data?.length ? (
          <ShowMore items={log.data} limit={8} noun="older emails" className="divide-y divide-slate-100 text-sm" render={(e) => (
              <li key={e.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>{e.subject} <span className="text-slate-400">to {e.to}</span></span>
                <span className="flex items-center gap-2 text-xs text-slate-500">{formatDateTime(e.created_at)} <Badge tone={e.status === 'SENT' ? 'green' : e.status === 'FAILED' ? 'red' : 'gray'}>{e.status}</Badge></span>
              </li>
            )} />
        ) : <p className="text-sm text-slate-500">Nothing sent yet.</p>}
      </Card>
    </div>
  )
}
