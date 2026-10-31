import { Link } from 'react-router-dom'

export function Logo({ light = false }: { light?: boolean }) {
  return (
    <Link to="/" className="leading-tight">
      <div className={`font-tamil text-xl font-bold ${light ? 'text-white' : 'text-maroon-700'}`}>கல்யாண மாலை</div>
      <div className={`text-[11px] uppercase tracking-[0.2em] ${light ? 'text-white/70' : 'text-stone-500'}`}>Shaandaar Events</div>
    </Link>
  )
}
