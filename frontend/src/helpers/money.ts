/** All money is integer paise. Convert only at the UI edge. */
const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

export function formatINR(paise: number | null | undefined): string {
  return inr.format((paise ?? 0) / 100)
}

/** Parses a rupee amount typed by a user ("1,25,000.50") into integer paise. */
export function rupeesToPaise(value: string | number): number {
  const n = typeof value === 'number' ? value : Number(value.replace(/[,\s₹]/g, ''))
  if (!Number.isFinite(n)) return 0
  return Math.round(n * 100)
}

export function paiseToRupees(paise: number | null | undefined): number {
  return (paise ?? 0) / 100
}
