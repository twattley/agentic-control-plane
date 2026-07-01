import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAvailableProjects, useRegisterRepo, useRepos } from '../../api/hooks'

function RegisterForm({ registeredPaths }: { registeredPaths: Set<string> }) {
  const register = useRegisterRepo()
  const { data: available, isLoading } = useAvailableProjects()
  const [selected, setSelected] = useState('')

  // Only offer folders not already registered.
  const choices = (available ?? []).filter((p) => !registeredPaths.has(p.path))

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const project = choices.find((p) => p.path === selected)
    if (!project) return
    register.mutate(
      { slug: project.name, name: project.name, path: project.path },
      { onSuccess: () => setSelected('') },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-semibold text-slate-800">Add a project</h2>
      <p className="text-xs text-slate-400">from your Projects folder</p>
      <select className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm"
        value={selected} onChange={(e) => setSelected(e.target.value)}>
        <option value="">
          {isLoading ? 'loading…' : choices.length ? 'select a folder…' : 'all folders registered'}
        </option>
        {choices.map((p) => (
          <option key={p.path} value={p.path}>
            {p.name}{!p.is_git && ' (not a git repo)'}
          </option>
        ))}
      </select>
      <button disabled={register.isPending || !selected}
        className="w-full rounded-lg bg-slate-900 py-2.5 font-medium text-white disabled:opacity-40">
        {register.isPending ? 'adding…' : 'Add project'}
      </button>
      {register.error && <p className="text-sm text-red-600">{String(register.error)}</p>}
    </form>
  )
}

export function Projects() {
  const { data: repos, isLoading } = useRepos()
  const registeredPaths = new Set((repos ?? []).map((r) => r.path))
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <header className="flex items-baseline justify-between pt-2">
        <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
        <Link to="/inbox" className="text-sm font-medium text-blue-600">Inbox →</Link>
      </header>

      <div className="space-y-2">
        {isLoading && <p className="text-sm text-slate-400">loading…</p>}
        {!isLoading && !repos?.length && <p className="text-sm text-slate-400">no projects yet</p>}
        {repos?.map((r) => (
          <Link key={r.id} to={`/projects/${r.id}`}
            className="block rounded-lg border border-slate-200 bg-white px-4 py-3 active:bg-slate-50">
            <div className="font-medium text-slate-900">{r.name}</div>
            <div className="truncate text-sm text-slate-500">{r.path}</div>
          </Link>
        ))}
      </div>

      <RegisterForm registeredPaths={registeredPaths} />
    </div>
  )
}
