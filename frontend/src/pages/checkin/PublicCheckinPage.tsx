import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { get, post } from '@/api/client'
import { formatDateTime } from '@/helpers/date'

interface PublicCheckin {
  vendor_name: string
  wedding_name: string
  function_name: string | null
  scheduled_arrival: string
  actual_arrival: string | null
  status: 'PENDING' | 'ON_TIME' | 'LATE'
  already_arrived: boolean
}

/** The page a vendor opens from their link on a phone. No login. */
export default function PublicCheckinPage() {
  const { token } = useParams()
  const info = useQuery({
    queryKey: ['public-checkin', token],
    queryFn: () => get<PublicCheckin>(`/public/checkin/${token}/`),
    retry: false,
  })
  const arrive = useMutation({
    mutationFn: () => post<PublicCheckin>(`/public/checkin/${token}/arrive/`),
    onSuccess: (data) => info.refetch().then(() => data),
  })
  const data = arrive.data ?? info.data

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 text-center shadow-lg">
        <p className="text-sm font-semibold text-brand-600">KalyaanaMaalai</p>
        {info.isLoading && <p className="py-10 text-slate-500">Loading…</p>}
        {info.error && (
          <p className="py-10 text-red-600" role="alert">
            This check-in link is not valid. Please ask your planner for a new one.
          </p>
        )}
        {data && (
          <>
            <h1 className="mt-3 text-2xl font-semibold">{data.vendor_name}</h1>
            <p className="mt-1 text-slate-600">
              {data.wedding_name}
              {data.function_name ? ` · ${data.function_name}` : ''}
            </p>
            <p className="mt-4 text-sm text-slate-500">Expected at</p>
            <p className="text-xl font-semibold">{formatDateTime(data.scheduled_arrival)}</p>

            {data.already_arrived ? (
              <div className="mt-6 rounded-xl bg-emerald-50 p-5 text-emerald-800" role="status">
                <p className="text-lg font-semibold">✓ You are checked in</p>
                <p className="mt-1 text-sm">Arrived at {formatDateTime(data.actual_arrival)}</p>
                <p className="mt-1 text-sm">{data.status === 'LATE' ? 'Marked as late.' : 'On time. Thank you!'}</p>
              </div>
            ) : (
              <>
                <button
                  onClick={() => arrive.mutate()}
                  disabled={arrive.isPending}
                  className="mt-6 w-full rounded-2xl bg-brand-600 px-6 py-5 text-xl font-semibold text-white active:bg-brand-700 disabled:opacity-60"
                >
                  {arrive.isPending ? 'Checking in…' : 'I have arrived'}
                </button>
                {arrive.error && (
                  <p className="mt-3 text-sm text-red-600" role="alert">
                    Could not check you in. Please try again.
                  </p>
                )}
              </>
            )}
          </>
        )}
      </div>
    </main>
  )
}
