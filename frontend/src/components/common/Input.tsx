import { forwardRef, type InputHTMLAttributes, type SelectHTMLAttributes, type ReactNode } from 'react'
import { cn } from './cn'

const base =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-100'

interface FieldProps {
  label?: string
  error?: string
}

function Field({ label, error, children }: FieldProps & { children: ReactNode }) {
  return (
    <label className="block text-sm">
      {label && <span className="mb-1 block font-medium text-slate-700">{label}</span>}
      {children}
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  )
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & FieldProps>(
  ({ label, error, className, ...rest }, ref) => (
    <Field label={label} error={error}>
      <input ref={ref} className={cn(base, error && 'border-red-400', className)} {...rest} />
    </Field>
  ),
)
Input.displayName = 'Input'

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & FieldProps>(
  ({ label, error, className, children, ...rest }, ref) => (
    <Field label={label} error={error}>
      <select ref={ref} className={cn(base, error && 'border-red-400', className)} {...rest}>
        {children}
      </select>
    </Field>
  ),
)
Select.displayName = 'Select'
