/** Reads the backend's live stream (Server-Sent Events) with `fetch`, so the login token can go in a header. */
export interface LiveEvent {
  id: number
  type: string
  data: Record<string, unknown>
  at: string
}

export class NotLoggedInError extends Error {}

export async function readStream(
  url: string,
  token: string,
  lastId: number,
  handlers: { onOpen: () => void; onEvent: (event: LiveEvent) => void },
  signal: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' }
  if (lastId) headers['Last-Event-ID'] = String(lastId) // the server replays what was missed

  const response = await fetch(url, { headers, signal })
  if (response.status === 401) throw new NotLoggedInError()
  if (!response.ok || !response.body) throw new Error(`Live stream failed (${response.status})`)
  handlers.onOpen()

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) return // the server closed it: the caller reconnects
    buffer += decoder.decode(value, { stream: true })
    let end: number
    while ((end = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, end)
      buffer = buffer.slice(end + 2)
      const data = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trim())
        .join('\n')
      if (data) handlers.onEvent(JSON.parse(data) as LiveEvent) // lines starting with ":" are keep-alives
    }
  }
}
