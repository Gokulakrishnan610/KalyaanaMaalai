import {
  BedDouble,
  Camera,
  Car,
  Flower2,
  Hand,
  Landmark,
  Mail,
  Music,
  Sparkles,
  UtensilsCrossed,
  type LucideIcon,
} from 'lucide-react'

/** The photos sit in customer-site/public/photos. If a file is missing, the slide shows a colour instead. */
export const SLIDES = [
  {
    image: '/photos/hero-1.jpg',
    colors: 'from-maroon-900 via-maroon-700 to-maroon-500',
    title: 'Your wedding, planned the way you imagined it',
    text: 'From the first phone call to the last guest leaving, one team looks after everything.',
  },
  {
    image: '/photos/hero-2.jpg',
    colors: 'from-stone-900 via-maroon-900 to-maroon-600',
    title: 'Every function, every little detail',
    text: 'Mehendi, sangeet, the wedding and the reception, planned together so nothing is missed.',
  },
  {
    image: '/photos/hero-3.jpg',
    colors: 'from-maroon-700 via-maroon-500 to-gold-500',
    title: 'Good vendors, honest prices',
    text: 'We ask three vendors for quotes and put them side by side, so you see what each one charges.',
  },
  {
    image: '/photos/hero-4.jpg',
    colors: 'from-maroon-900 via-maroon-600 to-gold-400',
    title: 'See where your wedding stands, and pay from your phone',
    text: 'Your account shows each step and your payments. Pay online when you are ready.',
  },
]

/** The codes match the backend (portal/serializers.py), so what a couple ticks reaches our CRM as it is. */
export const SERVICES: { code: string; label: string; text: string; icon: LucideIcon }[] = [
  { code: 'VENUE', label: 'Venue', text: 'Halls, lawns and resorts for your guest count', icon: Landmark },
  { code: 'CATERING', label: 'Catering', text: 'Menus and tastings, priced per plate', icon: UtensilsCrossed },
  { code: 'DECOR', label: 'Decor and stage', text: 'Mandap, flowers and lighting', icon: Flower2 },
  { code: 'PHOTOGRAPHY', label: 'Photo and video', text: 'Candid, traditional and films', icon: Camera },
  { code: 'MAKEUP', label: 'Makeup', text: 'Bridal and family makeup artists', icon: Sparkles },
  { code: 'MUSIC', label: 'Music and DJ', text: 'Sound, DJ and live performers', icon: Music },
  { code: 'MEHENDI', label: 'Mehendi', text: 'Artists for the bride and family', icon: Hand },
  { code: 'INVITATIONS', label: 'Invitations', text: 'Cards and digital invites', icon: Mail },
  { code: 'TRANSPORT', label: 'Transport', text: 'Cars and buses for you and guests', icon: Car },
  { code: 'STAY', label: 'Guest stay', text: 'Rooms for out-of-town family', icon: BedDouble },
]

export const FUNCTIONS = [
  { code: 'ENGAGEMENT', label: 'Engagement' },
  { code: 'MEHENDI', label: 'Mehendi' },
  { code: 'HALDI', label: 'Haldi' },
  { code: 'SANGEET', label: 'Sangeet' },
  { code: 'WEDDING', label: 'Wedding' },
  { code: 'RECEPTION', label: 'Reception' },
]

export const CONTACTS = [
  { code: 'CALL', label: 'Phone call' },
  { code: 'WHATSAPP', label: 'WhatsApp' },
  { code: 'EMAIL', label: 'Email' },
]

export const STEPS = [
  { title: 'Create your account', text: 'It takes two minutes. Just your name, phone and email.' },
  { title: 'Tell us about the wedding', text: 'Date, city, guests and what you need help with.' },
  { title: 'Our planner calls you', text: 'We talk, understand your plan and share a proposal.' },
  { title: 'We plan, you follow along', text: 'See each step in your account and pay online when it is time.' },
]

export const FAQ = [
  { q: 'Does it cost anything to create an account?', a: 'No. Creating an account and sharing your wedding details is free.' },
  { q: 'What happens after I sign up?', a: 'A planner from our team contacts you the way you prefer (call, WhatsApp or email) to talk about your wedding.' },
  { q: 'How do I pay?', a: 'Once your wedding is booked with us, your payments appear in your account with a Pay button. You can also pay us by cash, UPI or bank transfer if you like.' },
  { q: 'Who can see my details?', a: 'Only you and our planning team.' },
  { q: 'Can I change my details later?', a: 'Yes. Log in any time and update your profile.' },
]
