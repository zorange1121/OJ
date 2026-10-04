import Editor from "@monaco-editor/react"
import "../editor"
import { useCallback, useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { api, getToken, WS_BASE_URL } from "../api/client"
import type { ProblemDetail, SubmissionCreateResponse, SubmissionStatus, SubmissionUpdate } from "../api/types"

const DEFAULT_SOURCE = "\t; write your PIC18F4520 assembly here\n\tPROCESSOR p18f4520\n\n\tEND\n"

const STATUS_LABELS: Record<SubmissionStatus, string> = {
  Pending: "等待評測中",
  Compiling: "編譯中",
  Running: "評測中",
  AC: "Accepted",
  WA: "答案錯誤 (WA)",
  TLE: "超過時間限制 (TLE)",
  MLE: "超過記憶體限制 (MLE)",
  RE: "執行期錯誤 (RE)",
  CE: "編譯錯誤 (CE)",
}

const TERMINAL_STATUSES: SubmissionStatus[] = ["AC", "WA", "TLE", "MLE", "RE", "CE"]

export function ProblemDetailPage() {
  const { problemId } = useParams<{ problemId: string }>()
  const [problem, setProblem] = useState<ProblemDetail | null>(null)
  const [source, setSource] = useState(DEFAULT_SOURCE)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SubmissionUpdate | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const activeRef = useRef(true)

  useEffect(() => {
    if (!problemId) return
    api
      .get<ProblemDetail>(`/api/problems/${problemId}`)
      .then(setProblem)
      .catch((err) => setError(err instanceof Error ? err.message : "載入失敗"))
  }, [problemId])

  useEffect(() => {
    activeRef.current = true
    return () => {
      activeRef.current = false
      const socket = socketRef.current
      socketRef.current = null
      socket?.close()
      if (pollRef.current) clearTimeout(pollRef.current)
    }
  }, [])

  const submit = useCallback(async () => {
    if (!problemId) return
    setError(null)
    setResult(null)
    setSubmitting(true)
    const previousSocket = socketRef.current
    socketRef.current = null
    previousSocket?.close()
    if (pollRef.current) clearTimeout(pollRef.current)

    try {
      const created = await api.post<SubmissionCreateResponse>("/api/submissions", {
        problem_id: Number(problemId),
        source,
      })
      if (!activeRef.current) return
      setResult({ id: created.id, status: created.status, points: null, cycles: null, time: null, compile_output: null })

      const token = getToken()
      const socket = new WebSocket(`${WS_BASE_URL}/api/submissions/${created.id}/ws?token=${encodeURIComponent(token ?? "")}`)
      socketRef.current = socket
      let finished = false
      const poll = async () => {
        if (socketRef.current !== socket || finished) return
        try {
          const payload = await api.get<SubmissionUpdate>(`/api/submissions/${created.id}`)
          if (socketRef.current !== socket) return
          setResult(payload)
          if (TERMINAL_STATUSES.includes(payload.status)) {
            finished = true
            setSubmitting(false)
            setError(null)
            return
          }
        } catch {
          if (socketRef.current !== socket) return
          setError("連線中斷，正在重試查詢評測結果")
        }
        pollRef.current = setTimeout(poll, 3000)
      }

      socket.onmessage = (event) => {
        if (socketRef.current !== socket) return
        const payload: SubmissionUpdate = JSON.parse(event.data)
        setResult(payload)
        if (TERMINAL_STATUSES.includes(payload.status)) {
          finished = true
          setSubmitting(false)
          socket.close()
        }
      }
      socket.onerror = () => {
        socket.close()
      }
      socket.onclose = () => { void poll() }
    } catch (err) {
      setError(err instanceof Error ? err.message : "送出失敗")
      setSubmitting(false)
    }
  }, [problemId, source])

  if (error && !problem) return <p className="error">{error}</p>
  if (!problem) return <p>載入中...</p>

  return (
    <div className="problem-workspace">
      <Link className="back-link" to="/problems">← 返回題目總覽</Link>
      <h1>{problem.name}</h1>
      <p className="meta">
        配分 {problem.points} · 時限 {problem.time_limit}s · 出題者{" "}
        {problem.authors.map((a) => a.username).join(", ")}
      </p>
      <div className="workspace-grid">
      <section className="statement-panel"><div className="panel-heading"><h2>題目說明</h2><span className="points-badge">{problem.points} pts</span></div><p className="description">{problem.description}</p><div className="language-note">開發環境<strong>PIC18F4520 · MPASM</strong><span>提交單一組合語言原始檔。</span></div></section>
      <section className="coding-panel" aria-label="程式與評測">
      <div className="editor-wrapper">
        <div className="editor-toolbar"><span><span className="file-dot" />source.asm</span><span>MPASM</span></div>
        <Editor
          height="420px"
          theme="vs-dark"
          defaultLanguage="plaintext"
          value={source}
          onChange={(value) => setSource(value ?? "")}
          options={{ minimap: { enabled: false }, fontSize: 15, padding: { top: 20 }, scrollBeyondLastLine: false, automaticLayout: true }}
        />
      </div>

      <div className="submit-bar"><span className="meta">提交後將自動編譯並執行測資</span><button onClick={submit} disabled={submitting}>
        {submitting ? "評測中…" : "送出評測 →"}
      </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div aria-live="polite" className={`result-panel status-${result.status.toLowerCase()}`}>
          <div className="result-heading"><p className="status-label">{result.status === "AC" ? "✓ " : ""}{STATUS_LABELS[result.status]}</p><span>提交 #{result.id}</span></div>
          <div className="result-metrics">{result.points !== null && <div><span>得分</span><strong>{result.points}<small> / {problem.points}</small></strong></div>}
          {result.cycles !== null && <div><span>Instruction Cycles</span><strong>{result.cycles.toLocaleString()}</strong></div>}</div>
          {result.status === "CE" && result.compile_output && (
            <div>
              <p>編譯錯誤原因（source.asm 是你提交的程式，冒號後為行號）：</p>
              <pre className="compile-output">{result.compile_output}</pre>
            </div>
          )}
        </div>
      )}
      </section>
      </div>
    </div>
  )
}
