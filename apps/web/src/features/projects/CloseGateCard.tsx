import type { Repo } from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import { useSetCloseGate } from '../../api/hooks'

// The gate is the difference between "tests passed before this commit" and
// "nothing ran at all" — so an ungated repo says so in amber, never in silence.
export function CloseGateCard({ repo }: { repo: Repo }) {
  const update = useSetCloseGate(repo.id)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  const open = () => { setDraft(repo.close_gate_command ?? ''); setEditing(true) }
  const save = (command: string | null) =>
    update.mutate(command, { onSuccess: () => setEditing(false) })

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Close gate
          </div>
          {repo.close_gate_command ? (
            <code className="break-all text-sm text-slate-800">{repo.close_gate_command}</code>
          ) : (
            <p className="text-sm text-amber-700">
              ungated — the closer commits without running any check
            </p>
          )}
        </div>
        {!editing && (
          <button type="button" onClick={open}
            className="shrink-0 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-600 active:bg-slate-100">
            {repo.close_gate_command ? 'Edit' : 'Set gate'}
          </button>
        )}
      </div>
      {editing && (
        <div className="mt-2 space-y-2">
          <input autoFocus value={draft} onChange={(e) => setDraft(e.target.value)}
            placeholder="the repo's test command, e.g. make test"
            className="w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm" />
          <div className="flex gap-2">
            <button type="button" disabled={update.isPending || !draft.trim()}
              onClick={() => save(draft.trim())}
              className="flex-1 rounded-lg bg-slate-900 py-2 text-sm font-medium text-white disabled:opacity-40">
              {update.isPending ? 'saving…' : 'Save'}
            </button>
            {repo.close_gate_command && (
              <button type="button" disabled={update.isPending} onClick={() => save(null)}
                className="rounded-lg border border-amber-300 px-3 text-sm font-medium text-amber-700">
                Remove gate
              </button>
            )}
            <button type="button" onClick={() => setEditing(false)}
              className="rounded-lg border border-slate-300 px-4 text-sm text-slate-600">
              Cancel
            </button>
          </div>
        </div>
      )}
      {update.error && <p className="mt-2 text-sm text-red-600">{String(update.error)}</p>}
    </div>
  )
}
