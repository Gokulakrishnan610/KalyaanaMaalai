import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { cn } from '@/components/common'
import { formatINR } from '@/helpers/money'
import { sourceInfo, STATUSES, type Enquiry, type Status } from './types'

interface Props {
  enquiries: Enquiry[]
  canEdit: boolean
  onOpen: (enquiry: Enquiry) => void
  onMove: (enquiry: Enquiry, status: Status) => void
}

function Card({ enquiry, canEdit, onOpen }: { enquiry: Enquiry; canEdit: boolean; onOpen: Props['onOpen'] }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: String(enquiry.id),
    disabled: !canEdit,
  })
  const source = sourceInfo(enquiry.source)
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={() => onOpen(enquiry)}
      style={transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined}
      className={cn(
        'cursor-pointer rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm hover:border-brand-500',
        isDragging && 'z-10 opacity-80 shadow-lg',
      )}
    >
      <div className="font-medium">{enquiry.couple_name}</div>
      <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
        <span title={source.label}>
          {source.icon} {source.label}
        </span>
        {enquiry.guest_count && <span>{enquiry.guest_count} guests</span>}
      </div>
      {enquiry.budget_paise ? <div className="mt-1 text-xs text-slate-600">{formatINR(enquiry.budget_paise)}</div> : null}
    </div>
  )
}

function Column({ status, children, count }: { status: (typeof STATUSES)[number]; children: React.ReactNode; count: number }) {
  const { setNodeRef, isOver } = useDroppable({ id: status.value })
  return (
    <div
      ref={setNodeRef}
      className={cn('w-64 shrink-0 rounded-xl bg-slate-100 p-3', isOver && 'bg-brand-50 ring-2 ring-brand-500')}
    >
      <div className="mb-3 flex items-center justify-between text-sm font-semibold text-slate-700">
        {status.label}
        <span className="rounded-full bg-white px-2 text-xs font-medium text-slate-500">{count}</span>
      </div>
      <div className="min-h-16 space-y-2">{children}</div>
    </div>
  )
}

export function EnquiryBoard({ enquiries, canEdit, onOpen, onMove }: Props) {
  // a small distance before dragging starts, so a plain click still opens the enquiry
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  const handleDragEnd = (event: DragEndEvent) => {
    if (!event.over) return
    const enquiry = enquiries.find((e) => String(e.id) === String(event.active.id))
    const target = event.over.id as Status
    if (enquiry && enquiry.status !== target) onMove(enquiry, target)
  }

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STATUSES.map((status) => {
          const inColumn = enquiries.filter((e) => e.status === status.value)
          return (
            <Column key={status.value} status={status} count={inColumn.length}>
              {inColumn.map((e) => (
                <Card key={e.id} enquiry={e} canEdit={canEdit} onOpen={onOpen} />
              ))}
            </Column>
          )
        })}
      </div>
    </DndContext>
  )
}
