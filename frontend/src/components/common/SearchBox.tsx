import { Search, X } from 'lucide-react'
import { cn } from './cn'

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder: string
  label: string
  /** True while the results for what was typed are still on their way (typing paused or request running). */
  busy?: boolean
  className?: string
}

/** A search field with an icon, a clear button and a small spinner while results are loading.
 *  It only holds the text; pair it with `useDebouncedValue` so the server is not asked on every keystroke. */
export function SearchBox({ value, onChange, placeholder, label, busy, className }: Props) {
  return (
    <div className={cn('relative w-72 max-w-full', className)}>
      <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
      <input
        type="search"
        aria-label={label}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-9 text-sm outline-none transition-shadow focus:border-brand-500 focus:ring-2 focus:ring-brand-100 [&::-webkit-search-cancel-button]:hidden"
      />
      <span className="absolute right-2.5 top-1/2 -translate-y-1/2">
        {busy ? (
          <span role="status" aria-label="Searching" className="block h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        ) : (
          value && (
            <button type="button" aria-label="Clear search" onClick={() => onChange('')} className="rounded p-0.5 text-slate-400 hover:text-slate-700">
              <X size={14} />
            </button>
          )
        )}
      </span>
    </div>
  )
}
