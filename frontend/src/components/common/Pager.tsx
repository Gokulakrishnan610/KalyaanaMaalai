import { Button } from './Button'

interface Props {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
  noun: string
}

/** Previous / Next with "Showing 21-40 of 63 enquiries". Shows nothing when everything fits on one page. */
export function Pager({ page, pageSize, total, onPage, noun }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (pages <= 1) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return (
    <nav aria-label="Pages" className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
      <span>
        Showing {from}-{to} of {total} {noun}
      </span>
      <span className="flex items-center gap-3">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </Button>
        <span>
          Page {page} of {pages}
        </span>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </Button>
      </span>
    </nav>
  )
}
