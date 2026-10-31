import { IncidentsList } from './IncidentsList'

export default function IncidentsPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Incidents</h1>
      <p className="mb-5 text-sm text-slate-500">Problems reported during weddings. Planners are alerted the moment one is reported.</p>
      <IncidentsList />
    </div>
  )
}
