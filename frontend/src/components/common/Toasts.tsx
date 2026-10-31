import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { cn } from './cn'

type Tone = 'info' | 'warning' | 'critical' | 'success'

interface Toast {
  id: number
  message: string
  tone: Tone
}

const ToastContext = createContext<{ show: (message: string, tone?: Tone) => void } | null>(null)

const TONES: Record<Tone, string> = {
  info: 'border-sky-200 bg-white text-slate-800',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  warning: 'border-amber-300 bg-amber-50 text-amber-900',
  critical: 'border-red-300 bg-red-50 text-red-900',
}

/** Small pop-ups in the corner. Call `useToast().show("Saved")`; they close by themselves. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), [])

  const show = useCallback(
    (message: string, tone: Tone = 'info') => {
      const id = Date.now() + Math.random()
      setToasts((all) => [...all.slice(-3), { id, message, tone }]) // keep at most 4 on screen
      window.setTimeout(() => dismiss(id), tone === 'critical' ? 12000 : 6000)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ show }), [show])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
        {toasts.map((t) => (
          <button
            key={t.id}
            onClick={() => dismiss(t.id)}
            className={cn('pointer-events-auto rounded-xl border px-4 py-3 text-left text-sm shadow-lg', TONES[t.tone])}
          >
            {t.message}
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside ToastProvider')
  return context
}
