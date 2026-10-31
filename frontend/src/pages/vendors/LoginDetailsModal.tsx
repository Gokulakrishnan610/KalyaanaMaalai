import { useState } from 'react'
import { Button, Modal } from '@/components/common'

export interface VendorLogin {
  email: string
  password: string
}

/** Shown once, right after a vendor login is made: the person who added the vendor can pass it on (it was also emailed). */
export function LoginDetailsModal({ vendorName, login, onClose }: { vendorName: string; login: VendorLogin; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  const loginUrl = `${window.location.origin}/login`
  const text = `${vendorName} login\nWebsite: ${loginUrl}\nEmail: ${login.email}\nPassword: ${login.password}`
  return (
    <Modal open title="Vendor login created" onClose={onClose}>
      <p className="mb-3 text-sm text-slate-600">
        {vendorName} can now sign in on the main login page. We have emailed these details to {login.email}. This password is shown only now, so copy it if you want to share it another way.
      </p>
      <dl className="space-y-1 rounded-xl bg-slate-50 p-4 text-sm">
        <div><dt className="inline text-slate-500">Website: </dt><dd className="inline font-medium">{loginUrl}</dd></div>
        <div><dt className="inline text-slate-500">Email: </dt><dd className="inline font-medium">{login.email}</dd></div>
        <div><dt className="inline text-slate-500">Password: </dt><dd className="inline font-mono font-semibold">{login.password}</dd></div>
      </dl>
      <div className="mt-4 flex justify-end gap-2">
        <Button
          variant="secondary"
          onClick={() => {
            navigator.clipboard?.writeText(text)
            setCopied(true)
          }}
        >
          {copied ? 'Copied' : 'Copy details'}
        </Button>
        <Button onClick={onClose}>Done</Button>
      </div>
    </Modal>
  )
}
