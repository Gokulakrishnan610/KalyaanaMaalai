const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })

/** Amounts are whole paise everywhere; this shows them as rupees. */
export const formatINR = (paise: number | null | undefined) => inr.format((paise ?? 0) / 100)

export const rupeesToPaise = (value: string): number => {
  const n = Number(value.replace(/[,\s₹]/g, ''))
  return Number.isFinite(n) ? Math.round(n * 100) : 0
}

export const formatDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'

export const formatDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-'
