import type { ButtonHTMLAttributes } from 'react'
import { cn } from './cn'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

const styles: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white shadow-xs hover:bg-brand-700 disabled:bg-brand-600/50',
  secondary: 'bg-white text-slate-700 border border-slate-300 shadow-xs hover:bg-slate-50 hover:border-slate-400',
  danger: 'bg-white text-red-600 border border-red-200 hover:bg-red-50 hover:border-red-300 disabled:opacity-50',
  ghost: 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  /** sm for buttons inside tables and cards */
  size?: 'sm' | 'md'
  loading?: boolean
}

export function Button({ variant = 'primary', size = 'md', loading, className, children, disabled, ...rest }: Props) {
  return (
    <button
      className={cn(
        'btn inline-flex items-center justify-center gap-2 rounded-lg font-medium whitespace-nowrap focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 disabled:cursor-not-allowed',
        size === 'sm' ? 'h-8 px-3 text-xs' : 'h-9 px-4 text-sm',
        styles[variant],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />}
      {children}
    </button>
  )
}
