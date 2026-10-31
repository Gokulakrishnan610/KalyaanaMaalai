import { useEffect, useRef, useState } from 'react'

/** A box to draw a signature with a finger, pen or mouse. `onChange` gets a PNG data URL, or '' when it is empty. */
export function SignaturePad({ onChange }: { onChange: (png: string) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const drawing = useRef(false)
  const [empty, setEmpty] = useState(true)

  useEffect(() => {
    const c = canvas.current!
    const ctx = c.getContext('2d')!
    ctx.lineWidth = 2.5
    ctx.lineCap = 'round'
    ctx.strokeStyle = '#3b1020'
  }, [])

  const point = (e: React.PointerEvent) => {
    const rect = canvas.current!.getBoundingClientRect()
    return { x: ((e.clientX - rect.left) * canvas.current!.width) / rect.width, y: ((e.clientY - rect.top) * canvas.current!.height) / rect.height }
  }
  const down = (e: React.PointerEvent) => {
    canvas.current!.setPointerCapture(e.pointerId)
    drawing.current = true
    const ctx = canvas.current!.getContext('2d')!
    const { x, y } = point(e)
    ctx.beginPath()
    ctx.moveTo(x, y)
  }
  const move = (e: React.PointerEvent) => {
    if (!drawing.current) return
    const ctx = canvas.current!.getContext('2d')!
    const { x, y } = point(e)
    ctx.lineTo(x, y)
    ctx.stroke()
  }
  const up = () => {
    if (!drawing.current) return
    drawing.current = false
    setEmpty(false)
    onChange(canvas.current!.toDataURL('image/png'))
  }
  const clear = () => {
    const c = canvas.current!
    c.getContext('2d')!.clearRect(0, 0, c.width, c.height)
    setEmpty(true)
    onChange('')
  }

  return (
    <div>
      <canvas
        ref={canvas}
        width={600}
        height={200}
        aria-label="Draw your signature here"
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerLeave={up}
        className="h-36 w-full touch-none rounded-xl border-2 border-dashed border-stone-300 bg-white"
      />
      <div className="mt-1 flex justify-between text-xs text-stone-500">
        <span>{empty ? 'Draw your signature in the box' : 'Looks good'}</span>
        <button type="button" onClick={clear} className="font-medium text-maroon-700 hover:underline">Clear</button>
      </div>
    </div>
  )
}
