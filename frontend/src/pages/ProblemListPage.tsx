import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api } from "../api/client"
import type { ProblemListItem } from "../api/types"

export function ProblemListPage() {
  const [problems, setProblems] = useState<ProblemListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")

  useEffect(() => {
    api
      .get<ProblemListItem[]>("/api/problems")
      .then(setProblems)
      .catch((err) => setError(err instanceof Error ? err.message : "載入失敗"))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!problems) return <p>載入中...</p>

  const filtered = problems.filter(p => `${p.id} ${p.name}`.toLowerCase().includes(query.toLowerCase().trim()))
  return (
    <div>
      <div className="table-toolbar"><div><h1>題目列表</h1><span className="meta">{filtered.length} 題</span></div><input className="search-input" aria-label="搜尋題目" placeholder="搜尋題目名稱或編號…" value={query} onChange={e => setQuery(e.target.value)} /></div>
      <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>題目</th>
            <th>配分</th>
            <th>作答人數</th>
            <th>AC 率</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((p) => (
            <tr key={p.id}>
              <td>
                <Link className="problem-link" to={`/problems/${p.id}`}><span className="problem-id">{String(p.id).padStart(3, "0")}</span>{p.name}<span className="row-arrow">↗</span></Link>
              </td>
              <td><span className="points-badge">{p.points} pts</span></td>
              <td>{p.user_count}</td>
              <td><div className="rate-cell"><span>{(p.ac_rate * 100).toFixed(0)}%</span><span className="rate-track"><span style={{ width: `${Math.min(100, Math.max(0, p.ac_rate * 100))}%` }} /></span></div></td>
            </tr>
          ))}
        </tbody>
      </table>
      {filtered.length === 0 && <p className="empty-state">{problems.length ? "沒有符合的題目，試試其他關鍵字。" : "目前還沒有題目。"}</p>}
      </div>
    </div>
  )
}
