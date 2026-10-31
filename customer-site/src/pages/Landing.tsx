import { ChevronDown } from 'lucide-react'
import { Footer } from '@/components/Footer'
import { Navbar } from '@/components/Navbar'
import { Photo } from '@/components/Photo'
import { PhotoSlider } from '@/components/PhotoSlider'
import { LinkButton } from '@/components/ui'
import { FAQ, SERVICES, STEPS } from '@/data/content'

const GALLERY = [
  { src: '/photos/gallery-1.jpg', caption: 'Mehendi evening', className: 'aspect-[4/3]' },
  { src: '/photos/gallery-2.jpg', caption: 'The mandap', className: 'aspect-[4/3]' },
  { src: '/photos/gallery-3.jpg', caption: 'Sangeet night', className: 'aspect-[4/3]' },
  { src: '/photos/gallery-4.jpg', caption: 'Wedding table', className: 'aspect-[4/3]' },
  { src: '/photos/gallery-5.jpg', caption: 'Reception', className: 'aspect-[4/3]' },
]

const WHY = [
  { title: 'One team for everything', text: 'Venue, food, decor and music are planned together, so you talk to one person, not ten.' },
  { title: 'Prices you can compare', text: 'For big things like catering we ask three vendors and show you their quotes side by side.' },
  { title: 'Always know where you stand', text: 'Your account shows each step of the planning and your payments, any time of day.' },
]

export default function Landing() {
  return (
    <>
      <Navbar />
      <PhotoSlider>
        <LinkButton to="/signup" look="gold">
          Create your account
        </LinkButton>
        <a href="#how" className="inline-flex items-center justify-center gap-2 rounded-full border border-white/60 px-6 py-3 text-sm font-semibold text-white hover:bg-white/10">
          How it works
        </a>
      </PhotoSlider>

      <section id="gallery" className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-500">Moments we plan</p>
        <h2 className="mt-2 font-serif text-3xl font-semibold text-maroon-900 md:text-4xl">From the first haldi to the last dance</h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          {GALLERY.map((g) => (
            <Photo key={g.src} {...g} className={g.className} />
          ))}
          <div className="flex aspect-[4/3] flex-col justify-center rounded-2xl bg-maroon-600 p-8 text-white">
            <p className="font-serif text-2xl">Yours could be next.</p>
            <p className="mt-2 text-sm text-white/80">Tell us your date and we will take it from there.</p>
            <LinkButton to="/signup" look="gold" className="mt-5 self-start">
              Start planning
            </LinkButton>
          </div>
        </div>
      </section>

      <section id="services" className="bg-blush py-20">
        <div className="mx-auto max-w-6xl px-5">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-500">What we take care of</p>
          <h2 className="mt-2 font-serif text-3xl font-semibold text-maroon-900 md:text-4xl">Choose what you need, we handle the rest</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {SERVICES.map(({ code, label, text, icon: Icon }) => (
              <div key={code} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-stone-200/70">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-maroon-50 text-maroon-600">
                  <Icon size={22} />
                </div>
                <h3 className="mt-4 font-semibold text-maroon-900">{label}</h3>
                <p className="mt-1 text-sm text-stone-600">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-6xl px-5 py-20">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-500">How it works</p>
        <h2 className="mt-2 font-serif text-3xl font-semibold text-maroon-900 md:text-4xl">Four simple steps</h2>
        <ol className="mt-10 grid gap-6 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="relative rounded-2xl border border-stone-200 bg-white p-6">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-maroon-600 font-serif text-lg text-white">{i + 1}</span>
              <h3 className="mt-4 font-semibold text-maroon-900">{s.title}</h3>
              <p className="mt-1 text-sm text-stone-600">{s.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-maroon-900 py-20 text-white">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 md:grid-cols-3">
          {WHY.map((w) => (
            <div key={w.title}>
              <div className="mb-3 h-1 w-10 rounded bg-gold-400" />
              <h3 className="font-serif text-xl">{w.title}</h3>
              <p className="mt-2 text-sm text-white/75">{w.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-3xl px-5 py-20">
        <h2 className="font-serif text-3xl font-semibold text-maroon-900">Questions couples ask</h2>
        <div className="mt-8 divide-y divide-stone-200 rounded-2xl border border-stone-200 bg-white">
          {FAQ.map((item) => (
            <details key={item.q} className="group p-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium text-maroon-900">
                {item.q}
                <ChevronDown size={18} className="shrink-0 transition group-open:rotate-180" />
              </summary>
              <p className="mt-3 text-sm text-stone-600">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="px-5 pb-20">
        <div className="mx-auto max-w-4xl rounded-3xl bg-gradient-to-br from-maroon-600 to-maroon-900 p-10 text-center text-white md:p-14">
          <h2 className="font-serif text-3xl md:text-4xl">Ready to start planning?</h2>
          <p className="mx-auto mt-3 max-w-xl text-white/80">Create your account and tell us about your wedding. A planner will call you.</p>
          <LinkButton to="/signup" look="gold" className="mt-7">
            Create your account
          </LinkButton>
        </div>
      </section>
      <Footer />
    </>
  )
}
