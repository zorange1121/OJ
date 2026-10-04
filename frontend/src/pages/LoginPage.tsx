import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../auth/useAuth"
import { ApiError } from "../api/client"

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username, password)
      navigate("/problems")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登入失敗")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-layout">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1>picJudge</h1>
        <p className="meta">PIC18F4520 Online Judge</p>
        <label>
          帳號
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus autoComplete="username" placeholder="輸入帳號" />
        </label>
        <label>
          密碼
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" placeholder="輸入密碼" />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "登入中..." : "登入"}
        </button>
        <p className="hint">沒有帳號請聯絡管理員。</p>
      </form>
    </div>
  )
}
