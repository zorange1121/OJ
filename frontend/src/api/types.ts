export interface LoginResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
  is_admin: boolean
}

export interface UserOut {
  id: number
  username: string
}

export interface ProblemListItem {
  id: number
  name: string
  points: number
  user_count: number
  ac_rate: number
}

export interface ProblemDetail {
  id: number
  name: string
  description: string
  time_limit: number
  points: number
  user_count: number
  ac_rate: number
  authors: UserOut[]
}

export type SubmissionStatus =
  | "Pending"
  | "Compiling"
  | "Running"
  | "AC"
  | "WA"
  | "TLE"
  | "MLE"
  | "RE"
  | "CE"

export interface SubmissionCreateResponse {
  id: number
  status: SubmissionStatus
}

export interface SubmissionDetail {
  id: number
  user_id: number
  problem_id: number
  time: number | null
  points: number | null
  status: SubmissionStatus
  source: string
  cycles: number | null
  compile_output: string | null
  created_at: string | null
}

export interface SubmissionUpdate {
  id: number
  status: SubmissionStatus
  points: number | null
  cycles: number | null
  time: number | null
  compile_output: string | null
}

export interface LeaderboardEntry {
  rank: number
  user_id: number
  username: string
  total_score: number
}
