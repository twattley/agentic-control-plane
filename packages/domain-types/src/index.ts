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
/** `diff` remains the reviewer's full candidate. Revision artifacts preserve
 * human checkpoint baselines and their incremental response diffs. */
export type ArtifactKind =
  | 'diff'
  | 'test_output'
  | 'screenshot'
  | 'log'
  | 'evidence'
  | 'revision_base'
  | 'revision_diff'
export type Decision = 'approve' | 'request_changes' | 'block' | 'close'
export type QueueName = 'review' | 'fix' | 'human'

export interface Repo {
  id: number
  slug: string
  name: string
  path: string
  /** The repo's own close-gate command, run in its checkout before the closer
   * commits. null = ungated — allowed, and recorded on every run that closes
   * that way. */
  close_gate_command: string | null
  /** README first paragraph, derived at read time; null when there's no prose. */
  description: string | null
  created_at: string
}

/** Set or clear (null) a repo's close gate. Mirrors RepoGateIn. */
export interface RepoGateInput {
  close_gate_command: string | null
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

export interface RunRevision {
  checkpoint_event_id: number
  request_event_id: number | null
  request: string | null
  headline: string
  diff: string
  created_at: string
}

export interface RevisionRequest {
  event_id: number
  text: string
  created_at: string
}

/** Everything the phone needs to render one run. Mirrors RunDetail. */
export interface RunDetail {
  run: Run
  events: Event[]
  artifacts: Artifact[]
  leases: Lease[]
  revisions: RunRevision[]
  pending_revision_request: RevisionRequest | null
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

/** v2 adds standalone stories, making `epic_id` nullable. Both are read so
 * the portable tool can flip its emitter without blanking every project page. */
export type SchemaVersion = 'agent-workflow-snapshot-v1' | 'agent-workflow-snapshot-v2'

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
  /** null = a standalone story: first-class, with no parent epic. Only legal
   * from snapshot v2. */
  epic_id: string | null
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
  source: SchemaVersion | 'legacy-flat'
  schema_version: SchemaVersion | null
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
  /** null = standalone: a first-class story with no parent epic. Required for
   * repos that have no epics yet. */
  epic_id: string | null
  coordination_class: CoordinationClass
  title: string
  body?: string | null
}

/** Explicit legacy → story migration. Mirrors AdoptIn. */
export interface AdoptInput {
  legacy_id: string
  /** null adopts the ticket as a standalone story. */
  epic_id: string | null
  coordination_class: CoordinationClass
}

export interface AuthoredStory {
  story_id: string
  epic_id: string | null
  coordination_class: string
  state: string
  title: string
  path: string
}

/** Run the repo's own history sweep. Mirrors CompactIn; dry_run defaults true
 * server-side — the destructive direction must be asked for. */
export interface CompactInput {
  /** Only compact tickets completed before this YYYY-MM-DD date. */
  before?: string | null
  dry_run: boolean
}

export interface CompactedTicket {
  title: string
  completed: string
  path: string
  note: string
}

/** Mirror of `agent_workflow compact`'s payload (CompactResult). */
export interface CompactResult {
  ledger_file: string
  compacted: CompactedTicket[]
  archived_runs: string[]
  /** Completed-lane files with no Status block — documents, left alone. */
  preserved: string[]
  /** Runs still claimed whose ticket is gone: stale locks worth a look. */
  stale_claims: string[]
  dry_run: boolean
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
  skill_name: string | null
  created_at: string
  updated_at: string
}

export interface ShapingSkill {
  name: string
  description: string
}

export interface DiscussionStartInput {
  message: string
  skill_name?: string
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
