import type { BoardPane } from '@agentic-control-plane/domain-types'
import { Link } from 'react-router-dom'
import { useBoard } from '../../api/hooks'
import { StateBadge } from './StateBadge'

function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'now'
  if (s < 3600) return `${Math.floor(s / 60)}m`
  if (s < 86400) return `${Math.floor(s / 3600)}h`
  return `${Math.floor(s / 86400)}d`
}

function eventLine(pane: BoardPane): string | null {
  const e = pane.last_event
  if (!e) return null
  return `${e.type.split('_').join(' ')} · ${timeAgo(e.created_at)}`
}

function Pane({ pane }: { pane: BoardPane }) {
  const needsYou = pane.run.state === 'awaiting_human'
  return (
    <Link to={`/runs/${pane.run.id}`}
      className={`block rounded-lg border bg-white px-4 py-3 active:bg-slate-50 ${
        needsYou ? 'border-amber-400 ring-1 ring-amber-200' : 'border-slate-200'
      }`}>
      <div className="flex items-center justify-between gap-2">
        <div className="truncate font-medium text-slate-900">
          {pane.run.ticket_id} · {pane.run.title}
        </div>
        <StateBadge state={pane.run.state} />
      </div>
      {pane.summary && (
        <p className="mt-1 text-sm leading-snug text-slate-600 line-clamp-3">{pane.summary}</p>
      )}
      <div className="mt-1.5 text-xs text-slate-400">{eventLine(pane)}</div>
    </Link>
  )
}

export function Workbench() {
  const { data: panes } = useBoard()
  if (!panes?.length) return null

  // Group by project; within a group, runs waiting on the human come first.
  const byProject = new Map<string, BoardPane[]>()
  for (const p of panes) {
    const group = byProject.get(p.repo_name) ?? []
    group.push(p)
    byProject.set(p.repo_name, group)
  }
  const needsYouFirst = (a: BoardPane, b: BoardPane) =>
    Number(b.run.state === 'awaiting_human') - Number(a.run.state === 'awaiting_human')

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-800">Workbench</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {[...byProject.entries()].map(([project, group]) => (
          <div key={project} className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              {project}
            </h3>
            {group.sort(needsYouFirst).map((p) => <Pane key={p.run.id} pane={p} />)}
          </div>
        ))}
      </div>
    </section>
  )
}
