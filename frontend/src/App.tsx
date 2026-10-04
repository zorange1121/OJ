import { lazy, Suspense, type ReactNode } from "react"
import { Navigate, Route, Routes, Link, NavLink, useNavigate, useParams } from "react-router-dom"
import { AuthProvider } from "./auth/AuthContext"
import { useAuth } from "./auth/useAuth"
import { LoginPage } from "./pages/LoginPage"
import { ProblemListPage } from "./pages/ProblemListPage"
import { LeaderboardPage } from "./pages/LeaderboardPage"
import { CreateProblemPage } from "./pages/CreateProblemPage"

const ProblemDetailPage = lazy(() => import("./pages/ProblemDetailPage").then(module => ({ default: module.ProblemDetailPage })))

function ProblemRoute() {
  const { problemId } = useParams()
  return <Suspense fallback={<p>載入編輯器...</p>}><ProblemDetailPage key={problemId} /></Suspense>
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isAdmin } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!isAdmin) return <Navigate to="/problems" replace />
  return <>{children}</>
}

function Layout({ children }: { children: ReactNode }) {
  const { isAuthenticated, isAdmin, username, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate("/login")
  }

  return (
    <div className="app-shell">
      {isAuthenticated && (
        <nav className="nav" aria-label="主要導覽">
          <Link className="brand" to="/problems">picJudge</Link>
          <NavLink end to="/problems">題目總覽</NavLink>
          <NavLink to="/leaderboard">排行榜</NavLink>
          {isAdmin && <NavLink to="/admin/problems/new">建立題目</NavLink>}
          <span className="spacer" />
          <span className="user-chip"><span className="avatar">{username?.slice(0, 1).toUpperCase()}</span>{username}</span>
          <button className="link-button" onClick={handleLogout}>
            登出
          </button>
        </nav>
      )}
      <main className="content">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Layout>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/problems"
            element={
              <ProtectedRoute>
                <ProblemListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/problems/:problemId"
            element={
              <ProtectedRoute>
                <ProblemRoute />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/problems/new"
            element={
              <AdminRoute>
                <CreateProblemPage />
              </AdminRoute>
            }
          />
          <Route
            path="/leaderboard"
            element={
              <ProtectedRoute>
                <LeaderboardPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/problems" replace />} />
        </Routes>
      </Layout>
    </AuthProvider>
  )
}
