const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ""
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}`

const TOKEN_KEY = "picjudge_token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const resp = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })

  if (resp.status === 401) {
    clearToken()
    window.dispatchEvent(new Event("picjudge:unauthorized"))
  }

  if (!resp.ok) {
    let detail = resp.statusText
    const body = await resp.json().catch(() => null)
    if (body) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
    throw new ApiError(resp.status, detail)
  }

  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  postForm: <T,>(path: string, formData: FormData) => request<T>(path, { method: "POST", body: formData }),
}
