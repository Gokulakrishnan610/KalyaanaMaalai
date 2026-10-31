import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { Logo } from './Logo'
import { LinkButton } from './ui'

const LINKS = [
  { href: '/#services', label: 'Services' },
  { href: '/#how', label: 'How it works' },
  { href: '/#faq', label: 'Questions' },
]

export function Navbar() {
  const { loggedIn } = useAuth()
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-40 border-b border-stone-200/70 bg-ivory/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Logo />
        <nav className="hidden items-center gap-7 text-sm font-medium text-stone-600 md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="hover:text-maroon-700">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          {loggedIn ? (
            <LinkButton to="/home">My wedding</LinkButton>
          ) : (
            <>
              <Link to="/login" className="px-3 text-sm font-semibold text-maroon-700 hover:underline">
                Log in
              </Link>
              <LinkButton to="/signup">Start planning</LinkButton>
            </>
          )}
        </div>
        <button aria-label="Menu" className="md:hidden" onClick={() => setOpen((o) => !o)}>
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open && (
        <div className="space-y-3 border-t border-stone-200 bg-ivory px-5 py-4 md:hidden">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="block py-1 text-stone-700">
              {l.label}
            </a>
          ))}
          <div className="flex gap-3 pt-2">
            {loggedIn ? (
              <LinkButton to="/home" onClick={() => setOpen(false)}>My wedding</LinkButton>
            ) : (
              <>
                <LinkButton to="/login" look="outline" onClick={() => setOpen(false)}>Log in</LinkButton>
                <LinkButton to="/signup" onClick={() => setOpen(false)}>Start planning</LinkButton>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
