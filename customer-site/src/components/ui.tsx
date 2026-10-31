import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

export const cn = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(' ')

const base = 'inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50'
const looks = {
  primary: 'bg-maroon-600 text-white shadow-md shadow-maroon-600/25 hover:bg-maroon-700',
  gold: 'bg-gold-500 text-maroon-900 hover:bg-gold-400',
  outline: 'border border-maroon-600 text-maroon-700 hover:bg-maroon-50',
  light: 'border border-white/60 text-white hover:bg-white/10',
  ghost: 'text-stone-600 hover:bg-stone-100',
}
type Look = keyof typeof looks

export function Button({ look = 'primary', loading, className, children, disabled, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { look?: Look; loading?: boolean }) {
  return (
    <button className={cn(base, looks[look], className)} disabled={disabled || loading} {...rest}>
      {loading && <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  )
}

export function LinkButton({ look = 'primary', className, ...rest }: LinkProps & { look?: Look }) {
  return <Link className={cn(base, looks[look], className)} {...rest} />
}

export const Field = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string }>(
  ({ label, error, hint, className, ...rest }, ref) => (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-stone-700">{label}</span>
      <input
        ref={ref}
        className={cn(
          'w-full rounded-xl border bg-white px-4 py-3 text-base outline-none transition focus:border-maroon-500 focus:ring-4 focus:ring-maroon-100',
          error ? 'border-red-400' : 'border-stone-300',
          className,
        )}
        {...rest}
      />
      {hint && !error && <span className="mt-1 block text-xs text-stone-500">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  ),
)
Field.displayName = 'Field'

export function Chip({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        'rounded-full border px-4 py-2 text-sm font-medium transition',
        selected ? 'border-maroon-600 bg-maroon-600 text-white' : 'border-stone-300 bg-white text-stone-700 hover:border-maroon-500',
      )}
    >
      {children}
    </button>
  )
}
