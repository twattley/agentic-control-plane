import type { ProviderSpec, Run, RunMode, Ticket } from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link, useParams } from 'react-router-dom'
import {
  useCreateRun, useCreateTicket, useRepo, useRepoRuns,
  useTicket, useTickets, useUpdateTicket,
} from '../../api/hooks'
import { StateBadge } from '../runs/StateBadge'

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
        <div className="min-w-0">
          <div className="truncate font-medium text-slate-900">{ticket.title}</div>
          <div className="text-sm text-slate-500">tickets/{ticket.slug}.md</div>
        </div>
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

          {!active && (
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

  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Tickets</h2>
        {!composing && (
          <button type="button" onClick={() => setComposing(true)}
            className="text-sm font-medium text-blue-600">
            + New ticket
          </button>
        )}
      </div>
      {composing && <TicketComposer repoId={repoId} onDone={() => setComposing(false)} />}
      {tickets?.map((t) => (
        <TicketRow key={t.slug} repoId={repoId} ticket={t} runs={runs} />
      ))}
    </section>
  )
}

export function ProjectView() {
  const { id } = useParams()
  const repoId = Number(id)
  const { data: repo } = useRepo(repoId)
  const { data: runs } = useRepoRuns(repoId)

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <header className="space-y-1 pt-2">
        <Link to="/" className="text-sm text-slate-400">← projects</Link>
        <h1 className="text-2xl font-bold text-slate-900">{repo?.name ?? '…'}</h1>
      </header>

      <TicketList repoId={repoId} runs={runs ?? []} />

      <NewFeatureForm repoId={repoId} />

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
