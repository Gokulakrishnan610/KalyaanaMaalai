import type { HTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from './cn'

/** `lift` gives a hover outline; use it for cards that open something. */
export function Card({ className, lift, ...rest }: HTMLAttributes<HTMLDivElement> & { lift?: boolean }) {
  return <div className={cn('rounded-xl border border-slate-200 bg-white p-5 shadow-xs', lift && 'lift', className)} {...rest} />
}

export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn('mb-3 text-sm font-semibold text-slate-900', className)} {...rest} />
}

/** A card with a header row: title, an optional count, and a link or button on the right. */
export function Panel({ title, count, action, to, toLabel = 'View all', children, className, bodyClassName }: {
  title: ReactNode
  count?: number
  action?: ReactNode
  to?: string
  toLabel?: string
  children: ReactNode
  className?: string
  bodyClassName?: string
}) {
  return (
    <section className={cn('flex flex-col rounded-xl border border-slate-200 bg-white shadow-xs', className)}>
      <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          {title}
          {count !== undefined && <span className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600">{count}</span>}
        </h3>
        {action ?? (to && <Link to={to} className="text-xs font-medium text-brand-600 hover:text-brand-700">{toLabel}</Link>)}
      </header>
      <div className={cn('flex-1 px-5 py-4', bodyClassName)}>{children}</div>
    </section>
  )
}
