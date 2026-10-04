import { useEffect, useState } from "react"
import { api } from "../api/client"
import type { LeaderboardEntry } from "../api/types"

export function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<LeaderboardEntry[]>("/api/leaderboard")
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : "載入失敗"))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!entries) return <p>載入中...</p>

  return (
    <div>
      <section className="page-heading"><h1>排行榜</h1><span className="meta">{entries.length} 人</span></section>
      <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th>名次</th>
            <th>使用者</th>
            <th>總分</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.user_id}>
              <td><span className={`rank-badge rank-${e.rank}`}>{String(e.rank).padStart(2, "0")}</span></td>
              <td>{e.username}</td>
              <td><strong>{e.total_score}</strong><span className="meta"> pts</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      {entries.length === 0 && <p className="empty-state">尚無排名。</p>}
      </div>
    </div>
  )
}
