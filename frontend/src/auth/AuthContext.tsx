import { useCallback, useEffect, useState, type ReactNode } from "react"
import { api, clearToken, getToken, setToken } from "../api/client"
import { AuthContext } from "./useAuth"
import type { LoginResponse } from "../api/types"

const USERNAME_KEY = "picjudge_username"
const USER_ID_KEY = "picjudge_user_id"
const IS_ADMIN_KEY = "picjudge_is_admin"

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem(USERNAME_KEY))
  const [userId, setUserId] = useState<number | null>(() => {
    const raw = localStorage.getItem(USER_ID_KEY)
    return raw ? Number(raw) : null
  })
  const [isAdmin, setIsAdmin] = useState<boolean>(() => localStorage.getItem(IS_ADMIN_KEY) === "true")
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => Boolean(getToken()))

  const login = useCallback(async (usernameInput: string, password: string) => {
    const resp = await api.post<LoginResponse>("/api/auth/login", { username: usernameInput, password })
    setToken(resp.access_token)
    localStorage.setItem(USERNAME_KEY, resp.username)
    localStorage.setItem(USER_ID_KEY, String(resp.user_id))
    localStorage.setItem(IS_ADMIN_KEY, String(resp.is_admin))
    setUsername(resp.username)
    setUserId(resp.user_id)
    setIsAdmin(resp.is_admin)
    setIsAuthenticated(true)
  }, [])

  const logout = useCallback(() => {
    clearToken()
    localStorage.removeItem(USERNAME_KEY)
    localStorage.removeItem(USER_ID_KEY)
    localStorage.removeItem(IS_ADMIN_KEY)
    setUsername(null)
    setUserId(null)
    setIsAdmin(false)
    setIsAuthenticated(false)
  }, [])

  useEffect(() => {
    window.addEventListener("picjudge:unauthorized", logout)
    return () => window.removeEventListener("picjudge:unauthorized", logout)
  }, [logout])

  return (
    <AuthContext.Provider value={{ username, userId, isAdmin, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
