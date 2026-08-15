import type {
  CoordinationClass,
  ProviderSpec,
  Run,
  RunMode,
  Ticket,
  WorkflowLegacy,
  WorkflowProjection,
  WorkflowStory,
} from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link, useParams } from 'react-router-dom'
import {
  useAdoptLegacy, useCreateRun, useCreateStory, useCreateTicket, useMarkStoryReady,
  useRepo, useRepoRuns, useTicket, useTickets, useUpdateTicket, useWorkflow,
  useWorkflowDocument,
} from '../../api/hooks'
import { StateBadge } from '../runs/StateBadge'
import { DiscussionPanel } from './DiscussionPanel'

const TICKET_TEMPLATE = `# Title

## Summary

Two or three sentences written at freeze — enough for future-you to dive back in cold.

## Done means

- [ ] ...
`

function TicketComposer({ repoId, onDone }: { repoId: number; onDone: () => void }) {
  const create = useCreateTicket(repoId)
  const [slug, setSlug] = useState('')
  const [content, setContent] = useState(TICKET_TEMPLATE)

  const save = () => {
    if (!slug) return
    create.mutate({ slug, content }, { onSuccess: onDone })
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
      <input className="w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
        placeholder="ticket id, e.g. TR-1" value={slug}
        onChange={(e) => setSlug(e.target.value.trim())} />
      <textarea className="w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
        rows={14} value={content} onChange={(e) => setContent(e.target.value)} />
      <div className="flex gap-2">
        <button type="button" onClick={save} disabled={create.isPending || !slug}
          className="flex-1 rounded-lg bg-slate-900 py-2.5 font-medium text-white disabled:opacity-40">
          {create.isPending ? 'saving…' : 'Save ticket'}
        </button>
        <button type="button" onClick={onDone}
          className="rounded-lg border border-slate-300 px-4 text-sm text-slate-600">
          Cancel
        </button>
      </div>
      {create.error && <p className="text-sm text-red-600">{String(create.error)}</p>}
    </div>
  )
}

function TicketEditor({
  repoId, slug, initial, onDone,
}: { repoId: number; slug: string; initial: string; onDone: () => void }) {
  const update = useUpdateTicket(repoId)
  const [content, setContent] = useState(initial)

  return (
    <div className="space-y-2">
      <textarea className="w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
        rows={14} value={content} onChange={(e) => setContent(e.target.value)} />
      <div className="flex gap-2">
        <button type="button" disabled={update.isPending}
          onClick={() => update.mutate({ slug, content }, { onSuccess: onDone })}
          className="flex-1 rounded-lg bg-slate-900 py-2 font-medium text-white disabled:opacity-40">
          {update.isPending ? 'saving…' : 'Save'}
        </button>
        <button type="button" onClick={onDone}
          className="rounded-lg border border-slate-300 px-4 text-sm text-slate-600">
          Cancel
        </button>
      </div>
      {update.error && <p className="text-sm text-red-600">{String(update.error)}</p>}
    </div>
  )
}

// The agents on offer, as "provider[:model]" specs the worker expands into CLI
// flags. Defaults: Sonnet builds, Codex reviews.
const AGENTS: { value: ProviderSpec; label: string }[] = [
  { value: 'claude:sonnet', label: 'Claude Sonnet' },
  { value: 'claude:opus', label: 'Claude Opus' },
  { value: 'codex', label: 'Codex' },
  { value: 'stub', label: 'Stub (no-op)' },
]
const DEFAULT_BUILDER: ProviderSpec = 'claude:sonnet'
const DEFAULT_REVIEWER: ProviderSpec = 'codex'

function AgentPicker({
  builder, reviewer, onBuilder, onReviewer,
}: {
  builder: ProviderSpec
  reviewer: ProviderSpec
  onBuilder: (s: ProviderSpec) => void
  onReviewer: (s: ProviderSpec) => void
}) {
  const select = (value: ProviderSpec, onChange: (s: ProviderSpec) => void, label: string) => (
    <label className="flex flex-1 flex-col gap-1 text-xs font-medium text-slate-500">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="rounded border border-slate-300 bg-white px-2 py-2 text-sm font-normal text-slate-900">
        {AGENTS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
      </select>
    </label>
  )
  return (
    <div className="flex gap-2">
      {select(builder, onBuilder, 'builds')}
      {select(reviewer, onReviewer, 'reviews')}
    </div>
  )
}

function NewFeatureForm({ repoId }: { repoId: number }) {
  const create = useCreateRun(repoId)
  const [title, setTitle] = useState('')
  const [ticket, setTicket] = useState('')
  const [mode, setMode] = useState<RunMode>('direct')
  const [builder, setBuilder] = useState<ProviderSpec>(DEFAULT_BUILDER)
  const [reviewer, setReviewer] = useState<ProviderSpec>(DEFAULT_REVIEWER)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title) return
    create.mutate(
      {
        repo_id: repoId,
        ticket_id: ticket || title.toLowerCase().replace(/\s+/g, '-').slice(0, 40),
        title, mode, builder_provider: builder, reviewer_provider: reviewer,
      },
      { onSuccess: () => { setTitle(''); setTicket('') } },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-semibold text-slate-800">Start a feature</h2>
      <textarea className="w-full rounded border border-slate-300 px-3 py-2 text-sm" rows={3}
        placeholder="What should the builder do? (this becomes the task)"
        value={title} onChange={(e) => setTitle(e.target.value)} />
      <input className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        placeholder="ticket id (optional)" value={ticket} onChange={(e) => setTicket(e.target.value)} />

      <ModeToggle mode={mode} onChange={setMode} />
      <AgentPicker builder={builder} reviewer={reviewer}
        onBuilder={setBuilder} onReviewer={setReviewer} />

      <button disabled={create.isPending}
        className="w-full rounded-lg bg-blue-600 py-2.5 font-medium text-white disabled:opacity-40">
        {create.isPending ? 'starting…' : 'Start work'}
      </button>
      {create.error && <p className="text-sm text-red-600">{String(create.error)}</p>}
    </form>
  )
}

function ModeToggle({ mode, onChange }: { mode: RunMode; onChange: (m: RunMode) => void }) {
  return (
    <div className="flex gap-2">
      {(['direct', 'tdd'] as RunMode[]).map((m) => (
        <button key={m} type="button" onClick={() => onChange(m)}
          className={`flex-1 rounded-lg border py-2 text-sm font-medium ${
            mode === m ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 text-slate-600'
          }`}>
          {m === 'direct' ? 'Just build it' : 'Drive with tests'}
        </button>
      ))}
    </div>
  )
}

function TicketRow({ repoId, ticket, runs }: { repoId: number; ticket: Ticket; runs: Run[] }) {
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [mode, setMode] = useState<RunMode>('direct')
  const [builder, setBuilder] = useState<ProviderSpec>(DEFAULT_BUILDER)
  const [reviewer, setReviewer] = useState<ProviderSpec>(DEFAULT_REVIEWER)
  const create = useCreateRun(repoId)
  const { data: detail } = useTicket(repoId, open ? ticket.slug : null)

  // Latest run started from this ticket; only closed/blocked ones free it up again.
  const ticketRuns = runs.filter((r) => r.ticket_id === ticket.slug)
  const run = ticketRuns[ticketRuns.length - 1]
  const active = run && run.state !== 'closed' && run.state !== 'blocked'

  const start = () =>
    create.mutate({
      repo_id: repoId, ticket_id: ticket.slug, title: ticket.title, mode,
      builder_provider: builder, reviewer_provider: reviewer,
    })

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button type="button" onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left active:bg-slate-50">
        <div className="truncate font-medium text-slate-900">{ticket.title}</div>
        {run ? <StateBadge state={run.state} /> : <span className="text-slate-400">{open ? '▾' : '▸'}</span>}
      </button>

      {open && editing && detail && (
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          <TicketEditor repoId={repoId} slug={ticket.slug} initial={detail.content}
            onDone={() => setEditing(false)} />
        </div>
      )}

      {open && !editing && (
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          <div className="prose prose-sm prose-slate max-w-none overflow-x-auto">
            <ReactMarkdown>{detail?.content ?? ''}</ReactMarkdown>
          </div>

          <button type="button" onClick={() => setEditing(true)}
            className="w-full rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 active:bg-slate-50">
            Edit ticket
          </button>

          {run && (
            <Link to={`/runs/${run.id}`}
              className="block rounded-lg border border-slate-200 px-4 py-2 text-center text-sm font-medium text-slate-700 active:bg-slate-50">
              view run · {run.state}
            </Link>
          )}

          {!active && ticket.kind === 'ticket' && (
            <>
              <ModeToggle mode={mode} onChange={setMode} />
              <AgentPicker builder={builder} reviewer={reviewer}
                onBuilder={setBuilder} onReviewer={setReviewer} />
              <button type="button" onClick={start} disabled={create.isPending}
                className="w-full rounded-lg bg-blue-600 py-2.5 font-medium text-white disabled:opacity-40">
                {create.isPending ? 'starting…' : run ? 'Start another run' : 'Start work on this ticket'}
              </button>
            </>
          )}
          {create.error && <p className="text-sm text-red-600">{String(create.error)}</p>}
        </div>
      )}
    </div>
  )
}

function TicketList({ repoId, runs }: { repoId: number; runs: Run[] }) {
  const { data: tickets } = useTickets(repoId)
  const [composing, setComposing] = useState(false)
  const [shaping, setShaping] = useState(false)

  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-800">Tickets</h2>
        <div className="flex gap-3">
          {!shaping && (
            <button type="button" onClick={() => setShaping(true)}
              className="text-sm font-medium text-blue-600">
              Shape an idea
            </button>
          )}
          {!composing && (
            <button type="button" onClick={() => setComposing(true)}
              className="text-sm font-medium text-blue-600">
              + New ticket
            </button>
          )}
        </div>
      </div>
      {shaping && <DiscussionPanel repoId={repoId} onClose={() => setShaping(false)} />}
      {composing && <TicketComposer repoId={repoId} onDone={() => setComposing(false)} />}
      {tickets?.filter((t) => t.kind === 'ticket').map((t) => (
        <TicketRow key={t.slug} repoId={repoId} ticket={t} runs={runs} />
      ))}
      <DocsSection repoId={repoId} docs={tickets?.filter((t) => t.kind === 'doc') ?? []}
        runs={runs} />
    </section>
  )
}

function DocsSection({ repoId, docs, runs }: { repoId: number; docs: Ticket[]; runs: Run[] }) {
  const [open, setOpen] = useState(false)
  if (!docs.length) return null
  return (
    <div className="pt-1">
      <button type="button" onClick={() => setOpen(!open)}
        className="text-sm font-medium text-slate-400">
        {open ? '▾' : '▸'} Reference docs ({docs.length})
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {docs.map((t) => (
            <TicketRow key={t.slug} repoId={repoId} ticket={t} runs={runs} />
          ))}
        </div>
      )}
    </div>
  )
}

const CLASSES: CoordinationClass[] = ['feature', 'contract', 'platform', 'validation']

function NewStoryForm({
  repoId, workflow, onDone,
}: { repoId: number; workflow: WorkflowProjection; onDone: () => void }) {
  const create = useCreateStory(repoId)
  const [epicId, setEpicId] = useState(workflow.epics[0]?.epic_id ?? '')
  const [klass, setKlass] = useState<CoordinationClass>('feature')
  const [title, setTitle] = useState('')

  const save = () => {
    if (!title.trim() || !epicId) return
    create.mutate(
      { epic_id: epicId, coordination_class: klass, title: title.trim() },
      { onSuccess: onDone },
    )
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">
        Creates a canonical story skeleton in <code>backlog/</code> via the repo's own
        tool — shape it, then mark it ready.
      </p>
      <input className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        placeholder="story title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <div className="flex gap-2">
        <select value={epicId} onChange={(e) => setEpicId(e.target.value)}
          className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-2 py-2 text-sm">
          {workflow.epics.map((e) => (
            <option key={e.epic_id} value={e.epic_id}>{e.epic_id} · {e.title}</option>
          ))}
        </select>
        <select value={klass} onChange={(e) => setKlass(e.target.value as CoordinationClass)}
          className="rounded border border-slate-300 bg-white px-2 py-2 text-sm">
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="flex gap-2">
        <button type="button" onClick={save} disabled={create.isPending || !title.trim() || !epicId}
          className="flex-1 rounded-lg bg-slate-900 py-2.5 font-medium text-white disabled:opacity-40">
          {create.isPending ? 'creating…' : 'Create story'}
        </button>
        <button type="button" onClick={onDone}
          className="rounded-lg border border-slate-300 px-4 text-sm text-slate-600">
          Cancel
        </button>
      </div>
      {create.error && <p className="text-sm text-red-600">{String(create.error)}</p>}
    </div>
  )
}

function AdoptControls({
  repoId, legacyId, workflow,
}: { repoId: number; legacyId: string; workflow: WorkflowProjection }) {
  const adopt = useAdoptLegacy(repoId)
  const [epicId, setEpicId] = useState(workflow.epics[0]?.epic_id ?? '')
  const [klass, setKlass] = useState<CoordinationClass>('feature')

  return (
    <div className="space-y-2 border-t border-slate-100 pt-3">
      <p className="text-xs text-slate-500">
        Adopt as a story to make it startable — picks an identity under an epic;
        the legacy file's content moves in.
      </p>
      <div className="flex gap-2">
        <select value={epicId} onChange={(e) => setEpicId(e.target.value)}
          className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-2 py-2 text-sm">
          {workflow.epics.map((e) => (
            <option key={e.epic_id} value={e.epic_id}>{e.epic_id} · {e.title}</option>
          ))}
        </select>
        <select value={klass} onChange={(e) => setKlass(e.target.value as CoordinationClass)}
          className="rounded border border-slate-300 bg-white px-2 py-2 text-sm">
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <button type="button" disabled={adopt.isPending || !epicId}
          onClick={() => adopt.mutate({
            legacy_id: legacyId, epic_id: epicId, coordination_class: klass,
          })}
          className="rounded-lg bg-slate-900 px-4 text-sm font-medium text-white disabled:opacity-40">
          {adopt.isPending ? 'adopting…' : 'Adopt as story'}
        </button>
      </div>
      {adopt.error && <p className="text-sm text-red-600">{String(adopt.error)}</p>}
    </div>
  )
}

function WorkflowWorkRow({
  repoId, item, workflow, runs,
}: {
  repoId: number
  item: WorkflowStory | WorkflowLegacy
  workflow: WorkflowProjection
  runs: Run[]
}) {
  const identity = item.kind === 'story' ? item.story_id : item.legacy_id
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<RunMode>('direct')
  const [builder, setBuilder] = useState<ProviderSpec>(DEFAULT_BUILDER)
  const [reviewer, setReviewer] = useState<ProviderSpec>(DEFAULT_REVIEWER)
  const create = useCreateRun(repoId)
  const markReady = useMarkStoryReady(repoId)
  const { data: document, error: documentError } = useWorkflowDocument(
    repoId, open ? identity : null,
  )
  const matchingRuns = runs.filter((run) => run.ticket_id === identity)
  const currentRun = matchingRuns.find((run) => !['closed', 'blocked'].includes(run.state))
    ?? matchingRuns[0]
  const active = currentRun && !['closed', 'blocked'].includes(currentRun.state)
  const storyReady = item.kind === 'story'
    && item.state === 'ready'
    && item.claimable_roles.includes('builder')
    && item.diagnostic_codes.length === 0
  const legacyReady = item.kind === 'legacy' && workflow.ticket_contract === null
  const documentReady = document?.identity === identity && document.kind === item.kind
  const startable = (storyReady || legacyReady) && documentReady && !active

  const start = () => create.mutate({
    repo_id: repoId,
    ticket_id: identity,
    title: item.title,
    mode,
    builder_provider: builder,
    reviewer_provider: reviewer,
  })

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <button type="button" onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left active:bg-slate-50">
        <div className="min-w-0">
          <div className="truncate font-medium text-slate-900">{item.title}</div>
          <div className="flex flex-wrap gap-2 text-xs text-slate-500">
            <span>{identity}</span>
            {item.state && <span>state · {item.state}</span>}
            {item.kind === 'story' && <span>coordination · {item.coordination_class}</span>}
          </div>
        </div>
        {currentRun
          ? <StateBadge state={currentRun.state} />
          : <span className="text-slate-400">{open ? '▾' : '▸'}</span>}
      </button>

      {open && (
        <div className="space-y-3 border-t border-slate-100 px-4 py-3">
          {documentError && <p className="text-sm text-red-600">{String(documentError)}</p>}
          <div className="prose prose-sm prose-slate max-w-none overflow-x-auto">
            <ReactMarkdown>{document?.content ?? ''}</ReactMarkdown>
          </div>
          {item.kind === 'story' && item.diagnostic_codes.length > 0 && (
            <p className="text-sm text-amber-700">
              unavailable · {item.diagnostic_codes.join(', ')}
            </p>
          )}
          {currentRun && (
            <Link to={`/runs/${currentRun.id}`}
              className="block rounded-lg border border-slate-200 px-4 py-2 text-center text-sm font-medium text-slate-700">
              Control Plane run · {currentRun.state}
            </Link>
          )}
          {item.kind === 'legacy' && workflow.ticket_contract === 'epic-story-v1'
            && workflow.epics.length > 0 && !active && (
            <AdoptControls repoId={repoId} legacyId={item.legacy_id} workflow={workflow} />
          )}
          {item.kind === 'story' && item.state === 'backlog'
            && item.diagnostic_codes.length === 0 && !active && (
            <button type="button" disabled={markReady.isPending}
              onClick={() => markReady.mutate(item.story_id)}
              className="w-full rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 disabled:opacity-40">
              {markReady.isPending ? 'promoting…' : 'Mark ready'}
            </button>
          )}
          {markReady.error && <p className="text-sm text-red-600">{String(markReady.error)}</p>}
          {startable && (
            <>
              <ModeToggle mode={mode} onChange={setMode} />
              <AgentPicker builder={builder} reviewer={reviewer}
                onBuilder={setBuilder} onReviewer={setReviewer} />
              <button type="button" onClick={start} disabled={create.isPending}
                className="w-full rounded-lg bg-blue-600 py-2.5 font-medium text-white disabled:opacity-40">
                {create.isPending ? 'starting…' : 'Start work'}
              </button>
            </>
          )}
          {create.error && <p className="text-sm text-red-600">{String(create.error)}</p>}
        </div>
      )}
    </div>
  )
}

function WorkflowProject({
  repoId, workflow, runs,
}: { repoId: number; workflow: WorkflowProjection; runs: Run[] }) {
  const knownEpicIds = new Set(workflow.epics.map((epic) => epic.epic_id))
  const ungrouped = workflow.stories.filter((story) => !knownEpicIds.has(story.epic_id))
  const [shaping, setShaping] = useState(false)
  const [composing, setComposing] = useState(false)
  const [showLedgerNotes, setShowLedgerNotes] = useState(false)
  const [view, setView] = useState<'epics' | 'board'>('epics')
  // orphan_run = an old ledger record no longer joining to a current ticket —
  // history bookkeeping, not a problem with today's work. Everything else is.
  const ledgerNotes = workflow.diagnostics.filter((d) => d.code === 'orphan_run')
  const problems = workflow.diagnostics.filter((d) => d.code !== 'orphan_run')

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-0.5">
          {(['epics', 'board'] as const).map((v) => (
            <button key={v} type="button" onClick={() => setView(v)}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                view === v ? 'bg-slate-900 text-white' : 'text-slate-500'
              }`}>
              {v === 'epics' ? 'Epics' : 'Board'}
            </button>
          ))}
        </div>
        <div className="flex gap-3">
          {!shaping && (
            <button type="button" onClick={() => setShaping(true)}
              className="text-sm font-medium text-blue-600">
              Shape an idea
            </button>
          )}
          {!composing && (
            <button type="button" onClick={() => setComposing(true)}
              className="text-sm font-medium text-blue-600">
              + New story
            </button>
          )}
        </div>
      </div>
      {shaping && (
        <DiscussionPanel repoId={repoId} epics={workflow.epics}
          onClose={() => setShaping(false)} />
      )}
      {composing && (
        <NewStoryForm repoId={repoId} workflow={workflow}
          onDone={() => setComposing(false)} />
      )}
      {problems.length > 0 && (
        <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <h2 className="font-semibold text-amber-900">Workflow diagnostics</h2>
          {problems.map((diagnostic, index) => (
            <p key={`${diagnostic.code}-${diagnostic.path}-${index}`} className="text-sm text-amber-800">
              {diagnostic.source} · {diagnostic.code} · {diagnostic.message}
            </p>
          ))}
        </div>
      )}
      {ledgerNotes.length > 0 && (
        <div>
          <button type="button" onClick={() => setShowLedgerNotes(!showLedgerNotes)}
            className="text-sm font-medium text-slate-400">
            {showLedgerNotes ? '▾' : '▸'} Ledger history notes ({ledgerNotes.length})
          </button>
          {showLedgerNotes && (
            <div className="mt-2 space-y-1 rounded-lg border border-slate-200 bg-white p-3">
              {ledgerNotes.map((diagnostic, index) => (
                <p key={`${diagnostic.path}-${index}`} className="text-xs text-slate-500">
                  {diagnostic.message}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {view === 'board' ? (
        <StoryBoard repoId={repoId} workflow={workflow} runs={runs}
          items={[...workflow.stories, ...liveLegacyWork(workflow)]} />
      ) : (
        <>
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-slate-800">Epics</h2>
            {workflow.epics.map((epic) => (
              <EpicCard key={epic.epic_id} repoId={repoId} epic={epic}
                workflow={workflow} runs={runs} />
            ))}
          </div>

          {ungrouped.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-lg font-semibold text-slate-800">Ungrouped stories</h2>
              {ungrouped.map((story) => (
                <WorkflowWorkRow key={story.story_id} repoId={repoId} item={story}
                  workflow={workflow} runs={runs} />
              ))}
            </div>
          )}

          <LegacySection repoId={repoId} workflow={workflow} runs={runs} />
        </>
      )}

      {workflow.runs.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-lg font-semibold text-slate-800">Portable handoffs</h2>
          {workflow.runs.map((run) => (
            <div key={run.id} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
              <div className="font-medium text-slate-900">{run.work_unit_id}</div>
              <div className="text-sm text-slate-500">
                portable handoff · {run.role} · {run.status}
                {run.ticket_kind === null && ' · orphan'}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

// Lifecycle lanes, left to right. `complete` is deliberately absent — finished
// work leaves the board.
const LANES = ['backlog', 'ready', 'in-progress', 'blocked'] as const
const LANE_LABEL: Record<(typeof LANES)[number], string> = {
  backlog: 'Backlog',
  ready: 'Ready',
  'in-progress': 'In progress',
  blocked: 'Blocked',
}

function StoryBoard({
  repoId, workflow, runs, items,
}: {
  repoId: number
  workflow: WorkflowProjection
  runs: Run[]
  items: (WorkflowStory | WorkflowLegacy)[]
}) {
  return (
    <div className="-mx-4 overflow-x-auto px-4 pb-2">
      <div className="flex gap-3">
        {LANES.map((lane) => {
          const laneItems = items.filter((item) => item.state === lane)
          return (
            <div key={lane} className="w-72 shrink-0 space-y-2">
              <div className="flex items-baseline justify-between px-1">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {LANE_LABEL[lane]}
                </h3>
                <span className="text-xs text-slate-400">{laneItems.length}</span>
              </div>
              {!laneItems.length && (
                <p className="px-1 text-xs text-slate-300">empty</p>
              )}
              {laneItems.map((item) => (
                <WorkflowWorkRow key={item.path} repoId={repoId} item={item}
                  workflow={workflow} runs={runs} />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function EpicCard({
  repoId, epic, workflow, runs,
}: {
  repoId: number
  epic: WorkflowProjection['epics'][number]
  workflow: WorkflowProjection
  runs: Run[]
}) {
  const [open, setOpen] = useState(false)
  const stories = workflow.stories.filter((story) => story.epic_id === epic.epic_id)
  const activeCount = stories.filter((s) => s.state === 'in-progress').length

  return (
    <div className="rounded-xl border border-slate-300 bg-slate-50">
      <button type="button" onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-slate-900">{epic.title}</h3>
          <p className="text-xs text-slate-500">
            {epic.epic_id} · {stories.length} {stories.length === 1 ? 'story' : 'stories'}
            {activeCount > 0 && ` · ${activeCount} in progress`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {epic.story_counts.complete ?? 0}/{epic.story_counts.total ?? 0} complete
          </span>
          <span className="text-slate-400">{open ? '▾' : '▸'}</span>
        </div>
      </button>

      {open && (
        <div className="space-y-2 border-l-2 border-slate-300 px-3 pb-3 ml-4 mr-1">
          {!stories.length && <p className="px-1 text-sm text-slate-400">no stories yet</p>}
          {stories.map((story) => (
            <WorkflowWorkRow key={story.story_id} repoId={repoId} item={story}
              workflow={workflow} runs={runs} />
          ))}
        </div>
      )}
    </div>
  )
}

// Mirror of the backend's tickets-vs-docs rule: all-caps single words and
// these prefixes are reference material, not work.
const DOC_PREFIXES = ['handoff-', 'plan-', 're-fresh-', 'refresh-', 'human-', 'notes-']
function isDocStem(stem: string): boolean {
  return /^[A-Z]+$/.test(stem)
    || DOC_PREFIXES.some((p) => stem.toLowerCase().startsWith(p))
}

/** Legacy items that are still real, unfinished work — no completed history,
 * no reference docs. Shared by the legacy list and the board. */
function liveLegacyWork(workflow: WorkflowProjection): WorkflowLegacy[] {
  return workflow.legacy.filter(
    (item) => item.state !== 'complete' && !isDocStem(item.legacy_id),
  )
}

function LegacySection({
  repoId, workflow, runs,
}: { repoId: number; workflow: WorkflowProjection; runs: Run[] }) {
  const [showDocs, setShowDocs] = useState(false)
  // Completed history stays in the repo, not on screen; reference docs collapse.
  const live = workflow.legacy.filter((item) => item.state !== 'complete')
  const work = liveLegacyWork(workflow)
  const docs = live.filter((item) => isDocStem(item.legacy_id))
  if (!live.length) return null

  return (
    <div className="space-y-2">
      {work.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-slate-800">Legacy work</h2>
          {work.map((item) => (
            <WorkflowWorkRow key={item.path} repoId={repoId} item={item}
              workflow={workflow} runs={runs} />
          ))}
        </>
      )}
      {docs.length > 0 && (
        <div className="pt-1">
          <button type="button" onClick={() => setShowDocs(!showDocs)}
            className="text-sm font-medium text-slate-400">
            {showDocs ? '▾' : '▸'} Reference docs ({docs.length})
          </button>
          {showDocs && (
            <div className="mt-2 space-y-2">
              {docs.map((item) => (
                <WorkflowWorkRow key={item.path} repoId={repoId} item={item}
                  workflow={workflow} runs={runs} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function ProjectView() {
  const { id } = useParams()
  const repoId = Number(id)
  const { data: repo } = useRepo(repoId)
  const { data: runs } = useRepoRuns(repoId)
  const { data: workflow, error: workflowError } = useWorkflow(repoId)

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <header className="space-y-1 pt-2">
        <Link to="/" className="text-sm text-slate-400">← projects</Link>
        <h1 className="text-2xl font-bold text-slate-900">{repo?.name ?? '…'}</h1>
      </header>

      {workflowError && <p className="text-sm text-red-600">{String(workflowError)}</p>}
      {workflow?.source === 'legacy-flat' && <TicketList repoId={repoId} runs={runs ?? []} />}
      {workflow?.source === 'agent-workflow-snapshot-v1' && (
        <WorkflowProject repoId={repoId} workflow={workflow} runs={runs ?? []} />
      )}

      {workflow && workflow.ticket_contract !== 'epic-story-v1' && (
        <NewFeatureForm repoId={repoId} />
      )}

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-800">Features</h2>
        {!runs?.length && <p className="text-sm text-slate-400">no features yet</p>}
        {runs?.map((run) => (
          <Link key={run.id} to={`/runs/${run.id}`}
            className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 active:bg-slate-50">
            <div className="min-w-0">
              <div className="truncate font-medium text-slate-900">{run.title}</div>
              <div className="text-sm text-slate-500">
                {run.ticket_id}{run.mode === 'tdd' && ' · tests-first'}
              </div>
            </div>
            <StateBadge state={run.state} />
          </Link>
        ))}
      </section>
    </div>
  )
}
