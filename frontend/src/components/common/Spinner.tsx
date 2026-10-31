export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-14 text-sm text-slate-500" role="status">
      <span className="relative flex h-12 w-12 items-center justify-center">
        <span className="absolute inset-0 animate-spin rounded-full border-2 border-brand-100 border-t-brand-500" />
        <span className="absolute inset-2 rounded-full border-2 border-brand-100 border-b-brand-600" style={{ animation: 'spin-slow 1.6s linear infinite reverse' }} />
        <span className="h-2 w-2 rounded-full bg-brand-500 pulse-glow" />
      </span>
      <span className="animate-pulse">{label}</span>
    </div>
  )
}
