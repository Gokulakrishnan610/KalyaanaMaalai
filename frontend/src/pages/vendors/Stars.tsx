/** Five stars, filled to the given rating (partial stars are shown by clipping). */
export function Stars({ value, size = 'text-base' }: { value: number | null | undefined; size?: string }) {
  if (value == null) return <span className="text-xs text-slate-400">Not rated yet</span>
  const percent = Math.max(0, Math.min(5, value)) * 20
  return (
    <span className={`inline-flex items-center gap-1.5 ${size}`} title={`${value.toFixed(1)} out of 5`}>
      <span className="relative inline-block leading-none" aria-hidden="true">
        <span className="text-slate-300">★★★★★</span>
        <span className="absolute inset-y-0 left-0 overflow-hidden whitespace-nowrap text-amber-400" style={{ width: `${percent}%` }}>
          ★★★★★
        </span>
      </span>
      <span className="text-xs font-medium text-slate-600">{value.toFixed(1)}</span>
      <span className="sr-only">{value.toFixed(1)} out of 5 stars</span>
    </span>
  )
}

/** Clickable 1-5 stars for the rating form. */
export function StarPicker({ label, value, onChange }: { label: string; value: number; onChange: (n: number) => void }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="font-medium text-slate-700">{label}</span>
      <span role="radiogroup" aria-label={label} className="flex">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
            onClick={() => onChange(n)}
            className={`px-0.5 text-2xl leading-none ${n <= value ? 'text-amber-400' : 'text-slate-300 hover:text-amber-200'}`}
          >
            ★
          </button>
        ))}
      </span>
    </div>
  )
}
