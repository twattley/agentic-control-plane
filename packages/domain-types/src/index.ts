// TypeScript mirrors of the Python Pydantic models in apps/api.
// Keep these in sync with apps/api/app/features/*/models.py.

export type RunState =
  | 'queued'
  | 'building'
  | 'awaiting_review'
  | 'reviewing'
  | 'needs_work'
  | 'fixing'
  | 'awaiting_human'
  | 'approved'
  | 'closing'
  | 'closed'
  | 'blocked'

export type Role = 'builder' | 'reviewer' | 'human'
export type ArtifactKind = 'diff' | 'test_output' | 'screenshot' | 'log'
export type Decision = 'approve' | 'request_changes' | 'block' | 'close'
export type QueueName = 'review' | 'fix' | 'human'

export interface Repo {
  id: number
  slug: string
  name: string
  path: string
  created_at: string
}

export interface RepoInput {
  slug: string
  name: string
  path: string
}

export interface AvailableProject {
  name: string
  path: string
  is_git: boolean
}

export type RunMode = 'direct' | 'tdd'

export interface Run {
  id: number
  repo_id: number
  ticket_id: string
  title: string
  mode: RunMode
  state: RunState
  created_at: string
  updated_at: string
}

export interface RunInput {
  repo_id: number
  ticket_id: string
  title: string
  mode: RunMode
}

export interface Event {
  id: number
  run_id: number
  type: string
  actor: string
  payload: Record<string, unknown>
  created_at: string
}

export interface EventInput {
  type: string
  actor: string
  payload?: Record<string, unknown>
}

export interface Artifact {
  id: number
  run_id: number
  kind: ArtifactKind
  content: string
  created_at: string
}

export interface ArtifactInput {
  kind: ArtifactKind
  content: string
}

export interface Lease {
  id: number
  run_id: number
  role: Role
  holder: string
  acquired_at: string
  released_at: string | null
}

export interface ClaimInput {
  role: Role
  holder: string
}

export interface DecisionInput {
  decision: Decision
  note?: string | null
  actor?: string
}

/** Everything the phone needs to render one run. Mirrors RunDetail. */
export interface RunDetail {
  run: Run
  events: Event[]
  artifacts: Artifact[]
  leases: Lease[]
}
