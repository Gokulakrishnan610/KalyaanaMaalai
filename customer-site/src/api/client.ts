import axios, { AxiosError } from 'axios'

export const TOKEN_KEY = 'kmal_customer_token'

export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api' })

/** A failed request. `message` is ready to show; `fields` holds a message per form field. */
export class ApiError extends Error {
  status: number
  fields: Record<string, string>
  constructor(status: number, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// the server answers {"detail": "..."} or {"field": ["message"]}
function readError(status: number, body: unknown, fallback: string): ApiError {
  if (body && typeof body === 'object') {
    const data = body as Record<string, unknown>
    if (typeof data.detail === 'string') return new ApiError(status, data.detail)
    const fields: Record<string, string> = {}
    for (const [key, value] of Object.entries(data)) fields[key] = Array.isArray(value) ? String(value[0]) : String(value)
    const first = Object.values(fields)[0]
    if (first) return new ApiError(status, first, fields)
  }
  return new ApiError(status, fallback)
}

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    const status = err.response?.status ?? 0
    // an old or invalid login sends the person to the login page
    if (status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.assign('/login')
    }
    const offline = status === 0 ? 'We could not reach the server. Please try again in a moment.' : err.message
    return Promise.reject(readError(status, err.response?.data, offline))
  },
)

export const get = async <T>(url: string): Promise<T> => (await api.get<T>(url)).data
export const post = async <T>(url: string, body?: unknown): Promise<T> => (await api.post<T>(url, body)).data
export const patch = async <T>(url: string, body?: unknown): Promise<T> => (await api.patch<T>(url, body)).data
