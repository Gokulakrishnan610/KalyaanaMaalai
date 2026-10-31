import type { ReactNode } from 'react'
import { cn } from './cn'

type Tone = 'gray' | 'green' | 'red' | 'amber' | 'blue' | 'brand'

const tones: Record<Tone, string> = {
  gray: 'bg-slate-100 text-slate-700',
  green: 'bg-emerald-100 text-emerald-700',
  red: 'bg-red-100 text-red-700',
  amber: 'bg-amber-100 text-amber-800',
  blue: 'bg-sky-100 text-sky-700',
  brand: 'bg-brand-100 text-brand-700',
}

export function Badge({ tone = 'gray', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={cn('inline-block rounded-full px-2.5 py-0.5 text-xs font-medium', tones[tone])}>{children}</span>
}
