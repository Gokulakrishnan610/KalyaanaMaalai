import type { HTMLAttributes } from 'react'
import { cn } from './cn'

/** `lift` makes the card rise on hover; use it for cards that open something. */
export function Card({ className, lift, ...rest }: HTMLAttributes<HTMLDivElement> & { lift?: boolean }) {
  return <div className={cn('rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm', lift && 'lift', className)} {...rest} />
}

export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('mb-3 text-sm font-semibold text-slate-700', className)} {...rest} />
}
