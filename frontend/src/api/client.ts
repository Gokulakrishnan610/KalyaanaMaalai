import axios, { AxiosError } from 'axios'

export const TOKEN_KEY = 'km_token'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
})

/** Lists from the backend come in pages of 20: `?page=2` for the next one. */
export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** A failed request. `message` is ready to show the user; `fields` has per-field messages for forms. */
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

// Django sends {"detail": "..."} for most errors and {"field": ["message"]} for form errors.
function readError(status: number, body: unknown, fallback: string): ApiError {
  if (body && typeof body === 'object') {
    const data = body as Record<string, unknown>
    if (typeof data.detail === 'string') return new ApiError(status, data.detail)
    const fields: Record<string, string> = {}
    for (const [key, value] of Object.entries(data)) {
      const text = Array.isArray(value) ? String(value[0]) : String(value)
      fields[key] = text
    }
    const first = Object.values(fields)[0]
    if (first) return new ApiError(status, first, fields)
  }
  return new ApiError(status, fallback)
}

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    const status = err.response?.status ?? 0
    // an expired token sends the user back to the login page (but a wrong password just shows its error)
    if (status === 401 && !err.config?.url?.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.assign('/login')
    }
    return Promise.reject(readError(status, err.response?.data, err.message))
  },
)

// Small helpers: `const page = await get<Page<Enquiry>>('/enquiries/', { status: 'NEW' })`
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return (await api.get<T>(url, { params })).data
}
export async function post<T>(url: string, body?: unknown): Promise<T> {
  return (await api.post<T>(url, body)).data
}
export async function patch<T>(url: string, body?: unknown): Promise<T> {
  return (await api.patch<T>(url, body)).data
}
export async function remove(url: string): Promise<void> {
  await api.delete(url)
}
