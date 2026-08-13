import { Link } from 'react-router-dom'
import { useRepos } from '../../api/hooks'

export function Projects() {
  const { data: repos, isLoading } = useRepos()
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <header className="flex items-baseline justify-between pt-2">
        <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
        <Link to="/inbox" className="text-sm font-medium text-blue-600">Inbox →</Link>
      </header>

      <div className="space-y-2">
        {isLoading && <p className="text-sm text-slate-400">loading…</p>}
        {!isLoading && !repos?.length && (
          <p className="text-sm text-slate-400">
            no projects found — drop a git repo in your Projects folder and it appears here
          </p>
        )}
        {repos?.map((r) => (
          <Link key={r.id} to={`/projects/${r.id}`}
            className="block rounded-lg border border-slate-200 bg-white px-4 py-3 active:bg-slate-50">
            <div className="font-medium text-slate-900">{r.name}</div>
            {r.description && (
              <div className="mt-0.5 text-sm leading-snug text-slate-500">{r.description}</div>
            )}
          </Link>
        ))}
      </div>
    </div>
  )
}
