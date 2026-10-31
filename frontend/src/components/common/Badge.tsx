import type { ReactNode } from 'react'
import { cn } from './cn'

type Tone = 'gray' | 'green' | 'red' | 'amber' | 'blue' | 'brand'

// soft fill with a thin ring of the same colour: readable without shouting
const tones: Record<Tone, string> = {
  gray: 'bg-slate-50 text-slate-700 ring-slate-200',
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  red: 'bg-red-50 text-red-700 ring-red-200',
  amber: 'bg-amber-50 text-amber-800 ring-amber-200',
  blue: 'bg-sky-50 text-sky-700 ring-sky-200',
  brand: 'bg-brand-50 text-brand-700 ring-brand-200',
}

export function Badge({ tone = 'gray', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset', tones[tone])}>{children}</span>
}
