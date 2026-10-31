import { useMemo } from 'react'

const COLOURS = ['#e5395c', '#ffd98a', '#7c5cff', '#2bb07f', '#ff9f68', '#ffffff']

/** A short burst of falling confetti, for celebrating something done (like choosing a vendor). */
export function Confetti({ pieces = 70 }: { pieces?: number }) {
  const items = useMemo(
    () =>
      Array.from({ length: pieces }, (_, i) => ({
        left: Math.random() * 100,
        dx: (Math.random() - 0.5) * 240,
        rot: 360 + Math.random() * 720,
        delay: Math.random() * 0.6,
        duration: 2.2 + Math.random() * 1.6,
        size: 6 + Math.random() * 8,
        colour: COLOURS[i % COLOURS.length],
        round: i % 3 === 0,
      })),
    [pieces],
  )
  return (
    <div className="pointer-events-none fixed inset-0 z-[60] overflow-hidden" aria-hidden="true">
      {items.map((p, i) => (
        <span
          key={i}
          style={
            {
              position: 'absolute',
              top: 0,
              left: `${p.left}%`,
              width: p.size,
              height: p.size * (p.round ? 1 : 0.5),
              background: p.colour,
              borderRadius: p.round ? '9999px' : '2px',
              '--dx': `${p.dx}px`,
              '--rot': `${p.rot}deg`,
              animation: `confetti ${p.duration}s cubic-bezier(0.25, 0.6, 0.4, 1) ${p.delay}s both`,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  )
}
