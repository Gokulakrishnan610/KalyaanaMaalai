import type { HTMLAttributes, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { cn } from './cn'

export function Table({ className, ...rest }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
      <table className={cn('w-full text-left text-sm', className)} {...rest} />
    </div>
  )
}
export const Th = ({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) => (
  <th className={cn('h-10 border-b border-slate-200 bg-slate-50 px-4 text-xs font-medium whitespace-nowrap text-slate-500', className)} {...rest} />
)
export const Td = ({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) => (
  <td className={cn('border-b border-slate-100 px-4 py-3 align-middle text-slate-700 [tr:last-child>&]:border-b-0', className)} {...rest} />
)
