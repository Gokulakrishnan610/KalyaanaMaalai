import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { Badge } from './Badge'

type Tone = 'gray' | 'green' | 'red' | 'amber' | 'blue' | 'brand'

interface Props<T extends string> {
  value: T
  options: { value: T; label: string; tone?: Tone }[]
  onChange: (value: T) => void
  /** Plain badge, no dropdown (for people who may only look). */
  readOnly?: boolean
  label: string
}

/** A status badge that turns into a dropdown when clicked, so a status can be changed right in a table. */
export function StatusSelect<T extends string>({ value, options, onChange, readOnly, label }: Props<T>) {
  const [editing, setEditing] = useState(false)
  const current = options.find((o) => o.value === value)

  if (readOnly) return <Badge tone={current?.tone}>{current?.label ?? value}</Badge>

  if (editing) {
    return (
      <select
        autoFocus
        aria-label={label}
        value={value}
        // the row around it opens a form when clicked, so clicks here must not reach it
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          setEditing(false)
          if (e.target.value !== value) onChange(e.target.value as T)
        }}
        onBlur={() => setEditing(false)}
        className="rounded-lg border border-brand-500 bg-white px-2 py-1 text-sm outline-none ring-2 ring-brand-100"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    )
  }

  return (
    <button
      type="button"
      aria-label={`${label}: ${current?.label ?? value}. Click to change`}
      title="Click to change"
      onClick={(e) => {
        e.stopPropagation()
        setEditing(true)
      }}
      className="group inline-flex items-center gap-1 rounded-full transition-transform hover:scale-105 focus-visible:outline-2 focus-visible:outline-brand-500"
    >
      <Badge tone={current?.tone}>{current?.label ?? value}</Badge>
      <ChevronDown size={14} className="text-slate-400 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" />
    </button>
  )
}
