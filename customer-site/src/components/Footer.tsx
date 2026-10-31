import { Logo } from './Logo'

export function Footer() {
  return (
    <footer className="bg-maroon-900 py-12 text-white/80">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 md:flex-row md:items-end md:justify-between">
        <div>
          <Logo light />
          <p className="mt-3 max-w-sm text-sm">Wedding planning by Shaandaar Events. Create an account and our planner will get in touch.</p>
        </div>
        <p className="text-xs text-white/50">© {new Date().getFullYear()} Shaandaar Events</p>
      </div>
    </footer>
  )
}
