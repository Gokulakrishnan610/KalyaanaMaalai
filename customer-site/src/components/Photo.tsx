import { useState } from 'react'
import { cn } from './ui'

/** A photo from public/photos. If the file is not there yet, a soft colour with the caption is shown instead. */
export function Photo({ src, caption, className }: { src: string; caption: string; className?: string }) {
  const [missing, setMissing] = useState(false)
  return (
    <figure className={cn('group relative overflow-hidden rounded-2xl bg-gradient-to-br from-maroon-100 via-blush to-gold-400/40', className)}>
      {!missing && <img src={src} alt={caption} loading="lazy" className="h-full w-full object-cover transition duration-500 group-hover:scale-105" onError={() => setMissing(true)} />}
      <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-4 text-sm font-medium text-white">{caption}</figcaption>
    </figure>
  )
}
