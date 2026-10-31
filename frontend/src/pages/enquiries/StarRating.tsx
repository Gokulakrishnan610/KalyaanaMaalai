import { Star } from 'lucide-react'

/** 0 to 3 stars. Pass onChange to make it clickable; clicking the same star again clears it. */
export function StarRating({ value, onChange }: { value: number; onChange?: (value: number) => void }) {
  return (
    <span className="inline-flex gap-0.5" aria-label={`${value} of 3 stars`}>
      {[1, 2, 3].map((n) => {
        const star = <Star size={15} className={n <= value ? 'fill-amber-400 text-amber-400' : 'text-slate-300'} />
        return onChange ? (
          <button type="button" key={n} aria-label={`${n} star${n > 1 ? 's' : ''}`} onClick={() => onChange(value === n ? 0 : n)}>
            {star}
          </button>
        ) : (
          <span key={n}>{star}</span>
        )
      })}
    </span>
  )
}
