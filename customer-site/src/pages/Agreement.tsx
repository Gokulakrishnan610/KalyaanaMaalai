import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { ApiError, get, post } from '@/api/client'
import { useAuth } from '@/auth/AuthContext'
import { Logo } from '@/components/Logo'
import { SignaturePad } from '@/components/SignaturePad'
import { Button, Field } from '@/components/ui'
import { formatDateTime } from '@/helpers/money'

interface Certificate {
  signed_by: string
  signed_at: string
  ip: string | null
  hash: string
  text_unchanged: boolean
  company: string
  company_signer: string
  signature: string
}
interface Agreement {
  id: number
  title: string
  body: string
  wedding_title: string
  status: 'SENT' | 'SIGNED'
  certificate: Certificate | null
}

/** The agreement text: lines starting with "## " are headings, the rest are paragraphs and list lines. */
function Text({ body }: { body: string }) {
  return (
    <div className="space-y-2 text-[15px] leading-relaxed text-stone-700">
      {body.split('\n').map((line, i) =>
        line.startsWith('## ') ? <h3 key={i} className="pt-3 font-serif text-lg font-semibold text-maroon-900">{line.slice(3)}</h3> : line.trim() ? <p key={i}>{line}</p> : null,
      )}
    </div>
  )
}

export default function AgreementPage() {
  const { id } = useParams()
  const { loggedIn } = useAuth()
  const queryClient = useQueryClient()
  const agreement = useQuery({ queryKey: ['agreement', id], queryFn: () => get<Agreement>(`/portal/agreements/${id}/`), enabled: loggedIn })
  const [codeSent, setCodeSent] = useState('')
  const [form, setForm] = useState({ name: '', code: '', agreed: false, signature: '' })

  const askCode = useMutation({ mutationFn: () => post<{ detail: string }>(`/portal/agreements/${id}/code/`), onSuccess: (r) => setCodeSent(r.detail) })
  const sign = useMutation({
    mutationFn: () => post<Agreement>(`/portal/agreements/${id}/sign/`, form),
    onSuccess: (a) => queryClient.setQueryData(['agreement', id], a),
  })
  const errors = sign.error instanceof ApiError ? sign.error.fields : {}

  if (!loggedIn) return <Navigate to="/login" replace />
  if (agreement.isLoading) return <div className="p-10 text-center text-stone-500">Loading…</div>
  if (agreement.error || !agreement.data) return <div className="p-10 text-center text-stone-600">We could not find this agreement. <Link to="/home" className="font-semibold text-maroon-700">Go back</Link></div>
  const a = agreement.data
  const cert = a.certificate

  return (
    <div className="min-h-screen bg-ivory">
      <header className="border-b border-stone-200 bg-white print:hidden">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-5">
          <Logo />
          <Link to="/home" className="text-sm font-medium text-maroon-700 hover:underline">Back to my account</Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-6 px-5 py-8">
        <div>
          <h1 className="font-serif text-3xl font-semibold text-maroon-900">{a.title}</h1>
          <p className="text-stone-600">{a.wedding_title}</p>
        </div>
        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200 md:p-8"><Text body={a.body} /></section>

        {a.status === 'SIGNED' && cert ? (
          <section className="rounded-3xl bg-emerald-50 p-6 ring-1 ring-emerald-200">
            <div className="flex items-center gap-2 font-semibold text-emerald-800"><CheckCircle2 size={20} /> Signed by {cert.signed_by}</div>
            <p className="mt-1 text-sm text-emerald-900">{formatDateTime(cert.signed_at)}. Signed for {cert.company} by {cert.company_signer}.</p>
            <img src={cert.signature} alt="Your signature" className="mt-3 h-20 rounded-lg bg-white p-1" />
            <p className="mt-3 break-all text-xs text-stone-500">Fingerprint of this text: {cert.hash}{cert.text_unchanged ? ' (unchanged since you signed)' : ''}</p>
            <Button look="outline" className="mt-4 print:hidden" onClick={() => window.print()}>Print or save as PDF</Button>
          </section>
        ) : (
          <section className="space-y-4 rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200 md:p-8 print:hidden">
            <div className="flex items-center gap-2"><ShieldCheck size={20} className="text-maroon-600" /><h2 className="font-serif text-xl text-maroon-900">Sign this agreement</h2></div>
            <p className="text-sm text-stone-600">We will email you a 6-digit code to make sure it is really you.</p>
            <div className="flex flex-wrap items-center gap-3">
              <Button look="outline" loading={askCode.isPending} onClick={() => askCode.mutate()}>{codeSent ? 'Send the code again' : 'Email me a code'}</Button>
              {codeSent && <span className="text-sm text-emerald-700">{codeSent}</span>}
            </div>
            <Field label="Code from your email" inputMode="numeric" maxLength={6} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} error={errors.code} />
            <Field label="Your full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} error={errors.name} />
            <div>
              <span className="mb-1.5 block text-sm font-medium text-stone-700">Your signature</span>
              <SignaturePad onChange={(png) => setForm((f) => ({ ...f, signature: png }))} />
              {errors.signature && <span className="mt-1 block text-xs text-red-600">{errors.signature}</span>}
            </div>
            <label className="flex items-start gap-3 text-sm text-stone-700">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-maroon-600" checked={form.agreed} onChange={(e) => setForm({ ...form, agreed: e.target.checked })} />
              I have read this agreement and I agree to it. I understand that signing here is the same as signing on paper.
            </label>
            {errors.agreed && <p className="text-xs text-red-600">{errors.agreed}</p>}
            {sign.error && !Object.keys(errors).length && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{sign.error.message}</p>}
            <Button loading={sign.isPending} onClick={() => sign.mutate()}>Sign agreement</Button>
          </section>
        )}
      </main>
    </div>
  )
}
