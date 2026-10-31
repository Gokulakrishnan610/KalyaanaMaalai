import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { SLIDES } from '@/data/content'
import { cn } from './ui'

/** The big picture slider at the top of the home page. It changes slide by itself and stops while the mouse is on it. */
export function PhotoSlider({ children }: { children: ReactNode }) {
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const [missing, setMissing] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (paused) return
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % SLIDES.length), 6500)
    return () => window.clearInterval(timer)
  }, [paused])

  const go = (step: number) => setIndex((i) => (i + step + SLIDES.length) % SLIDES.length)

  return (
    <section
      className="relative isolate h-[34rem] overflow-hidden text-white md:h-[40rem]"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-roledescription="carousel"
      aria-label="Wedding photos"
    >
      {SLIDES.map((slide, i) => {
        const active = i === index
        return (
          <div key={slide.image} className={cn('absolute inset-0 transition-opacity duration-1000', active ? 'opacity-100' : 'opacity-0')} aria-hidden={!active}>
            {/* the colour is always there; a photo with the matching name covers it */}
            <div className={cn('absolute inset-0 bg-gradient-to-br', slide.colors)} />
            {!missing.has(slide.image) && (
              <img
                src={slide.image}
                alt=""
                className={cn('absolute inset-0 h-full w-full object-cover', active && 'slow-zoom')}
                onError={() => setMissing((m) => new Set(m).add(slide.image))}
              />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/25 to-black/30" />
          </div>
        )
      })}

      <div className="relative mx-auto flex h-full max-w-6xl flex-col justify-end px-5 pb-16 md:pb-24">
        <div key={index} className="max-w-2xl">
          <h1 className="font-serif text-4xl font-semibold leading-tight md:text-6xl">{SLIDES[index].title}</h1>
          <p className="mt-4 max-w-xl text-lg text-white/85">{SLIDES[index].text}</p>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">{children}</div>
      </div>

      <button aria-label="Previous photo" onClick={() => go(-1)} className="absolute left-3 top-1/2 hidden -translate-y-1/2 rounded-full bg-white/15 p-2 backdrop-blur hover:bg-white/30 md:block">
        <ChevronLeft />
      </button>
      <button aria-label="Next photo" onClick={() => go(1)} className="absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-full bg-white/15 p-2 backdrop-blur hover:bg-white/30 md:block">
        <ChevronRight />
      </button>
      <div className="absolute bottom-5 left-1/2 flex -translate-x-1/2 gap-2">
        {SLIDES.map((slide, i) => (
          <button key={slide.image} aria-label={`Show photo ${i + 1}`} onClick={() => setIndex(i)} className={cn('h-2 rounded-full transition-all', i === index ? 'w-8 bg-gold-400' : 'w-2 bg-white/60')} />
        ))}
      </div>
    </section>
  )
}
