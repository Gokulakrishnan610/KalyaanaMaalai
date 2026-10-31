import type { ReactNode } from 'react'

/** Two golden rings and a heart: the app's little wedding emblem, used on empty screens and the login page. */
export function Emblem({ className = 'h-20 w-20' }: { className?: string }) {
  return (
    <svg viewBox="0 0 96 96" className={className} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="emblem-rose" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ff7a93" />
          <stop offset="100%" stopColor="#b11a3b" />
        </linearGradient>
        <linearGradient id="emblem-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffd98a" />
          <stop offset="100%" stopColor="#e0a030" />
        </linearGradient>
      </defs>
      <circle cx="36" cy="54" r="22" stroke="url(#emblem-gold)" strokeWidth="5" />
      <circle cx="60" cy="54" r="22" stroke="url(#emblem-rose)" strokeWidth="5" />
      <path
        d="M48 30c-3-6-12-5-12 2 0 5 6 8 12 13 6-5 12-8 12-13 0-7-9-8-12-2z"
        fill="url(#emblem-rose)"
        className="twinkle"
        style={{ transformOrigin: '48px 36px' }}
      />
    </svg>
  )
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-dashed border-brand-500/30 bg-white/80 py-12 text-center">
      <div className="float mx-auto mb-3 w-fit opacity-90">
        <Emblem />
      </div>
      <p className="font-semibold text-slate-700">{title}</p>
      {hint && <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700" role="alert" style={{ animation: 'pop 0.35s ease-out both' }}>
      {message}
      {onRetry && (
        <button className="ml-3 font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
