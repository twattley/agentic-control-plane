import type { Artifact, Event, RunDetail as RunDetailData } from '@agentic-control-plane/domain-types'
import { Link, useParams } from 'react-router-dom'
import { useDecide, useDispatch, usePostEvent, useRun } from '../../api/hooks'
import { DiffView } from './DiffView'
import { StateBadge } from './StateBadge'

// States that are waiting on an agent — where a manual re-run makes sense.
const DISPATCHABLE = ['queued', 'awaiting_review', 'needs_work']

function payloadText(e: Event): string {
  const p = e.payload as Record<string, unknown>
  return (p.summary ?? p.brief ?? p.findings ?? p.note ?? p.text ?? '') as string
}

function latest(events: Event[], type: string): Event | undefined {
  return [...events].reverse().find((e) => e.type === type)
}

function latestDiff(artifacts: Artifact[]): Artifact | undefined {
  return [...artifacts].reverse().find((a) => a.kind === 'diff')
}

function ReRunButton({ id }: { id: number }) {
  const dispatch = useDispatch(id)
  return (
    <button
      onClick={() => dispatch.mutate()}
      disabled={dispatch.isPending}
      className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-600 active:bg-slate-100 disabled:opacity-40"
    >
      {dispatch.isPending ? 'dispatching…' : '↻ Re-run stage'}
    </button>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </section>
  )
}

function ActionBar({ data }: { data: RunDetailData }) {
  const id = data.run.id
  const decide = useDecide(id)
  const note = usePostEvent(id)
  const state = data.run.state
  const busy = decide.isPending || note.isPending

  const addNote = () => {
    const text = window.prompt('Note for the builder (a suggested edit, a question):')
    if (text) note.mutate({ type: 'human_note_posted', actor: 'human', payload: { note: text } })
  }
  const requestChanges = () => {
    const text = window.prompt('What needs changing?') ?? undefined
    decide.mutate({ decision: 'request_changes', note: text })
  }

  const canApprove = state === 'awaiting_human'
  const canBlock = !['approved', 'closing', 'closed', 'blocked'].includes(state)
  const canClose = state === 'approved'

  return (
    <div className="sticky bottom-0 -mx-4 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
      {(decide.error || note.error) && (
        <p className="mb-2 text-sm text-red-600">{String(decide.error ?? note.error)}</p>
      )}
      {canClose && (
        <button
          onClick={() => decide.mutate({ decision: 'close' })}
          disabled={busy}
          className="mb-2 w-full rounded-lg bg-slate-900 py-2.5 font-medium text-white disabled:opacity-40"
        >
          Submit — gate &amp; commit
        </button>
      )}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => decide.mutate({ decision: 'approve' })}
          disabled={busy || !canApprove}
          className="rounded-lg bg-green-600 py-2.5 font-medium text-white disabled:opacity-40"
        >
          Approve
        </button>
        <button
          onClick={requestChanges}
          disabled={busy || !canApprove}
          className="rounded-lg bg-amber-500 py-2.5 font-medium text-white disabled:opacity-40"
        >
          Request changes
        </button>
        <button
          onClick={addNote}
          disabled={busy}
          className="rounded-lg border border-slate-300 py-2.5 font-medium text-slate-700 disabled:opacity-40"
        >
          Add note
        </button>
        <button
          onClick={() => decide.mutate({ decision: 'block', note: 'blocked from dashboard' })}
          disabled={busy || !canBlock}
          className="rounded-lg border border-red-300 py-2.5 font-medium text-red-700 disabled:opacity-40"
        >
          Block
        </button>
      </div>
    </div>
  )
}

export function RunDetailPage() {
  const { id } = useParams()
  const { data, isLoading } = useRun(Number(id))

  if (isLoading || !data) return <p className="p-4 text-slate-400">loading…</p>

  const { run, events, artifacts } = data
  const brief = latest(events, 'builder_brief_posted')
  const findings = latest(events, 'reviewer_findings_posted')
  const diff = latestDiff(artifacts)

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col">
      <div className="flex-1 space-y-6 p-4">
        <header className="space-y-1">
          <Link to="/" className="text-sm text-slate-400">← inbox</Link>
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-xl font-bold text-slate-900">{run.title}</h1>
            <StateBadge state={run.state} />
          </div>
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-slate-500">{run.ticket_id}</p>
            {DISPATCHABLE.includes(run.state) && <ReRunButton id={run.id} />}
          </div>
        </header>

        {findings && (
          <Panel title="Reviewer findings">
            <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
              <span className="mr-2 font-medium">
                {(findings.payload as { verdict?: string }).verdict === 'pass' ? '✅ pass' : '✋ changes'}
              </span>
              {payloadText(findings) || <span className="text-slate-400">no detail</span>}
            </div>
          </Panel>
        )}

        {brief && (
          <Panel title="Builder brief">
            <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
              {payloadText(brief) || <span className="text-slate-400">no detail</span>}
            </div>
          </Panel>
        )}

        {diff && (
          <Panel title="Diff">
            <DiffView content={diff.content} />
          </Panel>
        )}

        <Panel title="Timeline">
          <ol className="space-y-1 text-sm">
            {events.map((e) => (
              <li key={e.id} className="flex gap-2 text-slate-600">
                <span className="text-slate-400">{e.actor}</span>
                <span className="font-medium">{e.type.replace(/_/g, ' ')}</span>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <ActionBar data={data} />
    </div>
  )
}
