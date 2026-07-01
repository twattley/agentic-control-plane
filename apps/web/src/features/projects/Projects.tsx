import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useRegisterRepo, useRepos } from '../../api/hooks'

function RegisterForm() {
  const register = useRegisterRepo()
  const [slug, setSlug] = useState('')
  const [name, setName] = useState('')
  const [path, setPath] = useState('')

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!slug || !path) return
    register.mutate(
      { slug, name: name || slug, path },
      { onSuccess: () => { setSlug(''); setName(''); setPath('') } },
    )
  }

  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="font-semibold text-slate-800">Register a project</h2>
      <input className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        placeholder="slug (e.g. racing-platform)" value={slug} onChange={(e) => setSlug(e.target.value)} />
      <input className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        placeholder="name (optional)" value={name} onChange={(e) => setName(e.target.value)} />
      <input className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
        placeholder="local checkout path (/Users/…/repo)" value={path} onChange={(e) => setPath(e.target.value)} />
      <button disabled={register.isPending}
        className="w-full rounded-lg bg-slate-900 py-2.5 font-medium text-white disabled:opacity-40">
        {register.isPending ? 'registering…' : 'Register project'}
      </button>
      {register.error && <p className="text-sm text-red-600">{String(register.error)}</p>}
    </form>
  )
}

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
        {!isLoading && !repos?.length && <p className="text-sm text-slate-400">no projects yet</p>}
        {repos?.map((r) => (
          <Link key={r.id} to={`/projects/${r.id}`}
            className="block rounded-lg border border-slate-200 bg-white px-4 py-3 active:bg-slate-50">
            <div className="font-medium text-slate-900">{r.name}</div>
            <div className="truncate text-sm text-slate-500">{r.path}</div>
          </Link>
        ))}
      </div>

      <RegisterForm />
    </div>
  )
}
