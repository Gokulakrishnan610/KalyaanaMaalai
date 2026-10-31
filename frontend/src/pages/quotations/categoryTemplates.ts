/** What each kind of vendor usually charges for. The quotation form shows these rows for the request's category.
 *  The labels stay the same for every vendor of a category, so the comparison table lines their prices up. */
export interface TemplateRow {
  label: string
  /** What the quantity counts: "hours", "guests", "people" ... */
  unit: string
  /** 'guests' starts the quantity at the request's guest count; a number is used as it is. */
  qty: 'guests' | number
}

export interface CategoryTemplate {
  rows: TemplateRow[]
  /** Caterers quote a price per plate. */
  perPlate?: boolean
  notesLabel: string
  notesHint: string
}

const row = (label: string, unit: string, qty: 'guests' | number = 1): TemplateRow => ({ label, unit, qty })

const TEMPLATES: Record<string, CategoryTemplate> = {
  Caterer: {
    perPlate: true,
    rows: [
      row('Buffet menu', 'guests', 'guests'),
      row('Welcome drinks', 'guests', 'guests'),
      row('Live counters', 'counters', 2),
      row('Dessert station', 'stations'),
      row('Midnight snacks', 'guests', 'guests'),
      row('Additional charges', 'items'),
    ],
    notesLabel: 'Menu notes',
    notesHint: 'Menu packages, food varieties, starters, Jain or special diets',
  },
  'DJ & Sound': {
    rows: [
      row('DJ charges', 'hours', 5),
      row('Sound system', 'sets'),
      row('Lighting', 'sets'),
      row('Additional equipment', 'items'),
      row('Extra hours (overtime)', 'hours', 0),
    ],
    notesLabel: 'Event notes',
    notesHint: 'Event duration, equipment list, setup time',
  },
  Photographer: {
    rows: [
      row('Photography package', 'packages'),
      row('Candid photography', 'hours', 8),
      row('Traditional photography', 'hours', 8),
      row('Videography', 'hours', 8),
      row('Additional photographers', 'people', 0),
      row('Albums and prints', 'albums', 0),
    ],
    notesLabel: 'Package notes',
    notesHint: 'Number of photographers, hours covered, deliverables and delivery time',
  },
  Videographer: {
    rows: [
      row('Videography package', 'packages'),
      row('Cinematic highlight film', 'films'),
      row('Drone coverage', 'hours', 0),
      row('Editing and delivery', 'items'),
    ],
    notesLabel: 'Package notes',
    notesHint: 'Hours covered, cameras, deliverables',
  },
  Decorator: {
    rows: [
      row('Decoration package', 'packages'),
      row('Stage decoration', 'stages'),
      row('Flower decoration', 'items'),
      row('Lighting', 'sets'),
      row('Entrance decoration', 'items'),
      row('Additional charges', 'items'),
    ],
    notesLabel: 'Decor notes',
    notesHint: 'Theme, colours, set-up and take-down timings',
  },
  Florist: {
    rows: [
      row('Flower arrangements', 'arrangements', 10),
      row('Garlands', 'garlands', 10),
      row('Loose flowers', 'kg', 20),
      row('Decoration charges', 'items'),
    ],
    notesLabel: 'Flower notes',
    notesHint: 'Flower types, colours, delivery time',
  },
  'Makeup Artist': {
    rows: [
      row('Bridal makeup', 'people'),
      row('Makeup package', 'packages', 0),
      row('Guest makeup', 'people', 0),
      row('Hairstyling', 'people', 0),
      row('Additional services', 'items', 0),
    ],
    notesLabel: 'Service notes',
    notesHint: 'Products used, trial session, travel',
  },
  'Mehendi Artist': {
    rows: [
      row('Bridal mehendi', 'people'),
      row('Guest mehendi', 'people', 0),
      row('Additional charges', 'items', 0),
    ],
    notesLabel: 'Service notes',
    notesHint: 'Designs, hours, number of artists',
  },
  Transport: {
    rows: [
      row('Vehicle rental', 'vehicles'),
      row('Extra distance', 'km', 0),
      row('Driver and waiting charges', 'hours', 0),
      row('Additional charges', 'items', 0),
    ],
    notesLabel: 'Vehicle notes',
    notesHint: 'Vehicle type, rental duration, distance included',
  },
  Venue: {
    rows: [
      row('Hall rental', 'days'),
      row('Catering at the venue', 'guests', 'guests'),
      row('Additional facilities', 'items', 0),
      row('Rooms', 'rooms', 0),
      row('Additional charges', 'items', 0),
    ],
    notesLabel: 'Venue notes',
    notesHint: 'Rental duration, guest capacity, catering availability, facilities included',
  },
  'Invitation Printer': {
    rows: [
      row('Invitation cards', 'cards', 'guests'),
      row('Design charges', 'items'),
      row('Envelopes and inserts', 'sets', 0),
      row('Additional charges', 'items', 0),
    ],
    notesLabel: 'Print notes',
    notesHint: 'Paper, size, finish, delivery date',
  },
}

const GENERIC: CategoryTemplate = {
  rows: [row('Service charges', 'items'), row('Additional charges', 'items', 0)],
  notesLabel: 'Notes',
  notesHint: 'What is included in the price',
}

export function templateFor(categoryName: string): CategoryTemplate {
  return TEMPLATES[categoryName] ?? GENERIC
}

export function normalise(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}
