import { ChevronDown } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

/** Shows the first `limit` items, then "Show N more" (or a link to the full page when `to` is given). */
export function ShowMore<T>({ items, limit = 5, render, to, noun = 'more', className = 'space-y-3' }: {
  items: T[]
  limit?: number
  render: (item: T, index: number) => ReactNode
  to?: string
  noun?: string
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const hidden = items.length - limit
  const shown = open || hidden <= 0 ? items : items.slice(0, limit)
  return (
    <>
      <ul className={className}>{shown.map(render)}</ul>
      {hidden > 0 && (
        to && !open ? (
          <Link to={to} className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700">
            See all {items.length} {noun}
          </Link>
        ) : (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-slate-900"
          >
            {open ? 'Show less' : `Show ${hidden} ${noun}`}
            <ChevronDown size={14} className={open ? 'rotate-180 transition-transform' : 'transition-transform'} />
          </button>
        )
      )}
    </>
  )
}
