import { cn } from '@/components/common'
import { useLiveStatus } from './LiveProvider'

const LABEL = { live: 'Live', connecting: 'Connecting…', offline: 'Reconnecting…' }

/** A small dot in the top bar: green when updates are arriving instantly. */
export function LiveStatus() {
  const status = useLiveStatus()
  return (
    <span
      title={status === 'live' ? 'Updates arrive instantly' : 'Trying to reconnect. The screen still refreshes every few seconds.'}
      className="hidden items-center gap-1.5 text-xs text-slate-500 sm:flex"
    >
      <span
        className={cn(
          'h-2 w-2 rounded-full',
          status === 'live' ? 'animate-pulse bg-emerald-500' : status === 'connecting' ? 'bg-amber-400' : 'bg-red-400',
        )}
      />
      {LABEL[status]}
    </span>
  )
}
