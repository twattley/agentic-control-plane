import type {
  Artifact, ArtifactKind, Event, RunDetail as RunDetailData,
} from '@agentic-control-plane/domain-types'
import { useState } from 'react'
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

function latestArtifact(artifacts: Artifact[], kind: ArtifactKind): Artifact | undefined {
  return [...artifacts].reverse().find((a) => a.kind === kind)
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

// Which gate ran before the close commit, and how it went. An ungated close
// reached `closed` without anything running — that must read as a warning,
// never as a green tick. Only an explicit `gate_command: null` means ungated:
// events from before the payload existed came from runs whose (then-global)
// gate really ran, so a missing key must not accuse them of skipping it.
function CloseGate({ event }: { event: Event }) {
  const payload = event.payload as { gate_command?: string | null }
  const failed = event.type === 'gate_failed'
  const badge = failed
    ? { label: '❌ gate failed', tone: 'text-red-700' }
    : payload.gate_command === null
      ? { label: '⚠ closed ungated — nothing was verified', tone: 'text-amber-700' }
      : { label: '✅ gate passed', tone: 'text-green-700' }

  return (
    <Panel title="Close gate">
      <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
        <span className={`mr-2 font-medium ${badge.tone}`}>{badge.label}</span>
        {payload.gate_command && (
          <code className="break-all text-slate-500">{payload.gate_command}</code>
        )}
        {!failed && payload.gate_command === undefined && (
          <span className="text-xs text-slate-400">gate command not recorded</span>
        )}
        {failed && (
          <p className="mt-1 whitespace-pre-wrap text-xs text-slate-500">{payloadText(event)}</p>
        )}
      </div>
    </Panel>
  )
}

function ActionBar({ data }: { data: RunDetailData }) {
  const id = data.run.id
  const decide = useDecide(id)
  const note = usePostEvent(id)
  const state = data.run.state
  const busy = decide.isPending || note.isPending

  // The most important text a human writes into this system, so it gets a real
  // control. `window.prompt` gave one unwrapped line with no way to review what
  // you had typed — and returned null on cancel, which is how a bounce with no
  // note reached the builder at all.
  const [composing, setComposing] = useState<'changes' | 'note' | null>(null)
  const [draft, setDraft] = useState('')

  const close = () => { setComposing(null); setDraft('') }
  const send = () => {
    const text = draft.trim()
    if (!text) return
    if (composing === 'changes') {
      decide.mutate({ decision: 'request_changes', note: text }, { onSuccess: close })
    } else {
      note.mutate(
        { type: 'human_note_posted', actor: 'human', payload: { note: text } },
        { onSuccess: close },
      )
    }
  }

  const canApprove = state === 'awaiting_human'
  const canBlock = !['approved', 'closing', 'closed', 'blocked'].includes(state)
  const canClose = state === 'approved'

  return (
    <div className="sticky bottom-0 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur">
      {(decide.error || note.error) && (
        <p className="mb-2 text-sm text-red-600">{String(decide.error ?? note.error)}</p>
      )}
      {composing && (
        <div className="mb-2 space-y-2">
          <textarea
            autoFocus
            rows={5}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={composing === 'changes'
              ? 'What needs changing? The builder reads this as its instruction.'
              : 'A note for the builder — a suggestion, a question.'}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={send}
              disabled={busy || !draft.trim()}
              className="flex-1 rounded-lg bg-slate-900 py-2.5 font-medium text-white disabled:opacity-40"
            >
              {busy ? 'sending…' : composing === 'changes' ? 'Request changes' : 'Add note'}
            </button>
            <button onClick={close} className="rounded-lg border border-slate-300 px-4 text-sm text-slate-600">
              Cancel
            </button>
          </div>
        </div>
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
          onClick={() => setComposing(composing === 'changes' ? null : 'changes')}
          disabled={busy || !canApprove}
          className="truncate rounded-lg bg-amber-500 py-2.5 font-medium text-white disabled:opacity-40"
        >
          Changes
        </button>
        <button
          onClick={() => setComposing(composing === 'note' ? null : 'note')}
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
  const briefText = brief ? payloadText(brief).replace(/\s+/g, ' ').trim() : ''
  const gate = [...events].reverse()
    .find((e) => e.type === 'gate_passed' || e.type === 'gate_failed')
  const diff = latestArtifact(artifacts, 'diff')

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col">
      <div className="min-w-0 flex-1 space-y-6 p-4">
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
          {briefText && <p className="truncate text-sm text-slate-600">{briefText}</p>}
        </header>

        {gate && <CloseGate event={gate} />}

        {diff && (
          <Panel title="Diff">
            <DiffView content={diff.content} />
          </Panel>
        )}

      </div>

      <ActionBar data={data} />
    </div>
  )
}
