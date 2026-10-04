import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { api, ApiError } from "../api/client"
import type { ProblemDetail } from "../api/types"

interface TestCaseRow {
  input_file: string
  output_file: string
  points: string
}

function emptyRow(): TestCaseRow {
  return { input_file: "", output_file: "", points: "0" }
}

export function CreateProblemPage() {
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [timeLimit, setTimeLimit] = useState("2.0")
  const [points, setPoints] = useState("100")
  const [testCases, setTestCases] = useState<TestCaseRow[]>([emptyRow()])
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function updateRow(index: number, field: keyof TestCaseRow, value: string) {
    setTestCases((rows) => rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }

  function addRow() {
    setTestCases((rows) => [...rows, emptyRow()])
  }

  function removeRow(index: number) {
    setTestCases((rows) => rows.filter((_, i) => i !== index))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!zipFile) {
      setError("請上傳測資 zip 檔")
      return
    }
    if (testCases.length === 0) {
      setError("至少要有一筆測資")
      return
    }

    setSubmitting(true)
    try {
      const formData = new FormData()
      formData.append("name", name)
      formData.append("description", description)
      formData.append("time_limit", timeLimit)
      formData.append("points", points)
      formData.append(
        "testcases",
        JSON.stringify(
          testCases.map((row) => ({
            input_file: row.input_file,
            output_file: row.output_file,
            points: Number(row.points),
          })),
        ),
      )
      formData.append("zipfile", zipFile)

      const created = await api.postForm<ProblemDetail>("/api/problems", formData)
      navigate(`/problems/${created.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "建立題目失敗")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1>建立題目</h1>
      <form className="card form-wide" onSubmit={handleSubmit}>
        <label>
          題目名稱
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          題目描述
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={5} required />
        </label>
        <div className="row">
          <label>
            時間限制（秒）
            <input
              type="number"
              step="0.1"
              min="0"
              value={timeLimit}
              onChange={(e) => setTimeLimit(e.target.value)}
              required
            />
          </label>
          <label>
            配分
            <input type="number" step="1" min="0" value={points} onChange={(e) => setPoints(e.target.value)} required />
          </label>
        </div>

        <h2>測資</h2>
        <p className="hint">
          每一筆對應 zip 檔裡的一組輸入/輸出檔案（會拿去給 gpsim 的 -c script 用，檔名要跟你的 .stc 腳本一致）。
        </p>
        {testCases.map((row, i) => (
          <div className="row testcase-row" key={i}>
            <input
              placeholder="input_file，例如 1.in"
              value={row.input_file}
              onChange={(e) => updateRow(i, "input_file", e.target.value)}
              required
            />
            <input
              placeholder="output_file，例如 1.out"
              value={row.output_file}
              onChange={(e) => updateRow(i, "output_file", e.target.value)}
              required
            />
            <input
              type="number"
              placeholder="配分"
              value={row.points}
              onChange={(e) => updateRow(i, "points", e.target.value)}
              required
            />
            <button type="button" className="secondary" onClick={() => removeRow(i)} disabled={testCases.length === 1}>
              移除
            </button>
          </div>
        ))}
        <button type="button" className="secondary" onClick={addRow}>
          新增一筆測資
        </button>

        <label>
          測資 zip 檔
          <input
            type="file"
            accept=".zip"
            onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? "建立中..." : "建立題目"}
        </button>
      </form>
    </div>
  )
}
