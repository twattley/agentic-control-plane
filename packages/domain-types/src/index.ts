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
/** `evidence` is optional markdown a builder leaves to demonstrate the outcome
 * — a case table of real inputs and actual outputs. */
export type ArtifactKind = 'diff' | 'test_output' | 'screenshot' | 'log' | 'evidence'
export type Decision = 'approve' | 'request_changes' | 'block' | 'close'
export type QueueName = 'review' | 'fix' | 'human'

export interface Repo {
  id: number
  slug: string
  name: string
  path: string
  /** README first paragraph, derived at read time; null when there's no prose. */
  description: string | null
  created_at: string
}

export type RunMode = 'direct' | 'tdd'

/** Agent choice as "provider[:model]" — e.g. "claude:sonnet", "codex", "stub".
 * null falls back to the API's global provider setting. */
export type ProviderSpec = string

export interface Run {
  id: number
  repo_id: number
  ticket_id: string
  title: string
  mode: RunMode
  state: RunState
  builder_provider: ProviderSpec | null
  reviewer_provider: ProviderSpec | null
  created_at: string
  updated_at: string
}

export interface RunInput {
  repo_id: number
  ticket_id: string
  title: string
  mode: RunMode
  builder_provider?: ProviderSpec | null
  reviewer_provider?: ProviderSpec | null
}

export interface DispatchInput {
  provider?: ProviderSpec | null
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

/** A markdown file in the repo checkout's tickets/ folder. Mirrors Ticket. */
export interface Ticket {
  slug: string
  title: string
  /** 'ticket' = startable work; 'doc' = reference material (handoffs, plans,
   * READMEs) shown collapsed. */
  kind: 'ticket' | 'doc'
  /** Re-entry blurb: the `## Summary` section written at ticket freeze,
   * else the first prose paragraph. */
  summary: string | null
}

export interface TicketDetail extends Ticket {
  content: string
}

export interface TicketCreateInput {
  slug: string
  content: string
}

export interface TicketUpdateInput {
  content: string
}

export interface WorkflowEpic {
  kind: 'epic'
  epic_id: string
  title: string
  path: string
  story_ids: string[]
  story_counts: Record<string, number>
}

export interface WorkflowStory {
  kind: 'story'
  story_id: string
  epic_id: string
  coordination_class: string
  state: string
  title: string
  path: string
  claimable_roles: string[]
  diagnostic_codes: string[]
}

export interface WorkflowLegacy {
  kind: 'legacy'
  legacy_id: string
  title: string
  path: string
  state: string | null
}

export interface PortableWorkflowRun {
  id: string
  project_slug: string
  work_unit_id: string
  ticket_path: string
  agent: string
  role: string
  status: string
  ticket_kind: 'story' | 'legacy' | null
  last_event: string | null
}

export interface WorkflowDiagnostic {
  source: string
  code: string
  message: string
  path: string
  related_paths: string[]
}

export interface WorkflowProjection {
  source: 'agent-workflow-snapshot-v1' | 'legacy-flat'
  schema_version: 'agent-workflow-snapshot-v1' | null
  ticket_contract: 'epic-story-v1' | null
  epics: WorkflowEpic[]
  stories: WorkflowStory[]
  legacy: WorkflowLegacy[]
  runs: PortableWorkflowRun[]
  diagnostics: WorkflowDiagnostic[]
}

export interface WorkflowDocument {
  identity: string
  kind: 'epic' | 'story' | 'legacy'
  path: string
  title: string
  summary: string | null
  content: string
}

export type CoordinationClass = 'contract' | 'platform' | 'feature' | 'validation'

/** Author a story via the repo's own create-story tool. Mirrors StoryCreateIn. */
export interface StoryCreateInput {
  epic_id: string
  coordination_class: CoordinationClass
  title: string
  body?: string | null
}

/** Explicit legacy → story migration. Mirrors AdoptIn. */
export interface AdoptInput {
  legacy_id: string
  epic_id: string
  coordination_class: CoordinationClass
}

export interface AuthoredStory {
  story_id: string
  epic_id: string
  coordination_class: string
  state: string
  title: string
  path: string
}

/** A ticket-shaping discussion — the strand that exists before a ticket is
 * frozen. Mirrors Discussion. */
export type DiscussionState = 'open' | 'frozen'

export interface Discussion {
  id: number
  repo_id: number
  session_id: string | null
  state: DiscussionState
  ticket_slug: string | null
  created_at: string
  updated_at: string
}

export interface DiscussionMessage {
  id: number
  discussion_id: number
  role: 'human' | 'agent'
  content: string
  created_at: string
}

export interface DiscussionDetail {
  discussion: Discussion
  messages: DiscussionMessage[]
}

/** One workbench pane: an active run plus everything needed to re-enter it
 * cold. Mirrors BoardPane. */
export interface BoardPane {
  run: Run
  repo_name: string
  summary: string | null
  last_event: Event | null
}
