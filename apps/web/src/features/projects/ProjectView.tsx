import type { RunMode } from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useCreateRun, useRepo, useRepoRuns } from '../../api/hooks'
import { StateBadge } from '../runs/StateBadge'

function NewFeatureForm({ repoId }: { repoId: number }) {
  const create = useCreateRun(repoId)
  const [title, setTitle] = useState('')
  const [ticket, setTicket] = useState('')
  const [mode, setMode] = useState<RunMode>('direct')

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!title) return
    create.mutate(
      { repo_id: repoId, ticket_id: ticket || title.toLowerCase().replace(/\s+/g, '-').slice(0, 40), title, mode },
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

      <div className="flex gap-2">
        {(['direct', 'tdd'] as RunMode[]).map((m) => (
          <button key={m} type="button" onClick={() => setMode(m)}
            className={`flex-1 rounded-lg border py-2 text-sm font-medium ${
              mode === m ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 text-slate-600'
            }`}>
            {m === 'direct' ? 'Just build it' : 'Drive with tests'}
          </button>
        ))}
      </div>

      <button disabled={create.isPending}
        className="w-full rounded-lg bg-blue-600 py-2.5 font-medium text-white disabled:opacity-40">
        {create.isPending ? 'starting…' : 'Start work'}
      </button>
      {create.error && <p className="text-sm text-red-600">{String(create.error)}</p>}
    </form>
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
        <p className="truncate text-sm text-slate-500">{repo?.path}</p>
      </header>

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
