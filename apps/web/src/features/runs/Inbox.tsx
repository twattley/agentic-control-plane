import type { QueueName, Run } from '@agentic-control-plane/domain-types'
import { Link } from 'react-router-dom'
import { useQueue } from '../../api/hooks'
import { StateBadge } from './StateBadge'

const SECTIONS: { name: QueueName; title: string; blurb: string }[] = [
  { name: 'human', title: 'Waiting on you', blurb: 'approve, request changes, or note' },
  { name: 'review', title: 'Waiting on review', blurb: 'reviewer to pick up' },
  { name: 'fix', title: 'Waiting on a fix', blurb: 'builder to address findings' },
]

function RunCard({ run }: { run: Run }) {
  return (
    <Link
      to={`/runs/${run.id}`}
      className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 active:bg-slate-50"
    >
      <div className="min-w-0">
        <div className="truncate font-medium text-slate-900">{run.title}</div>
        <div className="truncate text-sm text-slate-500">{run.ticket_id}</div>
      </div>
      <StateBadge state={run.state} />
    </Link>
  )
}

function QueueSection({ name, title, blurb }: { name: QueueName; title: string; blurb: string }) {
  const { data: runs, isLoading } = useQueue(name)
  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
        <span className="text-xs text-slate-400">{blurb}</span>
      </div>
      {isLoading && <p className="text-sm text-slate-400">loading…</p>}
      {!isLoading && !runs?.length && <p className="text-sm text-slate-400">nothing here</p>}
      <div className="space-y-2">
        {runs?.map((run) => <RunCard key={run.id} run={run} />)}
      </div>
    </section>
  )
}

export function Inbox() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <header className="pt-2">
        <Link to="/" className="text-sm text-slate-400">← projects</Link>
        <h1 className="text-2xl font-bold text-slate-900">Inbox</h1>
        <p className="text-sm text-slate-500">builder / reviewer handoff — needs attention</p>
      </header>
      {SECTIONS.map((s) => <QueueSection key={s.name} {...s} />)}
    </div>
  )
}
