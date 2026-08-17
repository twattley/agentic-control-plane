import type { CompactResult } from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import { useCompact } from '../../api/hooks'

// The sweep every close performs, exposed for backlogs that accumulated before
// delegation existed. Two clicks by design: a dry run shows exactly what would
// move, and only confirming runs the real thing.
export function CompactCard({ repoId }: { repoId: number }) {
  const compact = useCompact(repoId)
  const [preview, setPreview] = useState<CompactResult | null>(null)
  const [swept, setSwept] = useState<CompactResult | null>(null)

  const dryRun = () =>
    compact.mutate({ dry_run: true }, { onSuccess: (r) => { setSwept(null); setPreview(r) } })
  const sweep = () =>
    compact.mutate({ dry_run: false }, { onSuccess: (r) => { setPreview(null); setSwept(r) } })

  const summary = (r: CompactResult) =>
    `${r.compacted.length} ticket${r.compacted.length === 1 ? '' : 's'} → ${r.ledger_file}, ` +
    `${r.archived_runs.length} run${r.archived_runs.length === 1 ? '' : 's'} → archive`

  return (
    <section className="space-y-2">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Completed history
      </h2>
      <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm text-slate-500">
          Sweep aged completed tickets into the done ledger and archive their runs
          — the same tidy-up every close performs.
        </p>

        {preview && (
          <div className="space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-sm font-medium text-slate-700">Would move: {summary(preview)}</p>
            {preview.compacted.map((t) => (
              <p key={t.path} className="truncate text-xs text-slate-500">
                {t.title} · {t.completed}
              </p>
            ))}
            {!preview.compacted.length && !preview.archived_runs.length && (
              <p className="text-xs text-slate-400">nothing old enough to sweep</p>
            )}
            {preview.stale_claims.length > 0 && (
              <p className="text-xs text-amber-700">
                {preview.stale_claims.length} stale claim(s) worth a look:{' '}
                {preview.stale_claims.join(', ')}
              </p>
            )}
          </div>
        )}
        {swept && (
          <p className="text-sm text-green-700">Swept: {summary(swept)}</p>
        )}

        <div className="flex gap-2">
          <button type="button" onClick={dryRun} disabled={compact.isPending}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-40">
            {compact.isPending ? 'working…' : 'Preview sweep'}
          </button>
          {preview && (preview.compacted.length > 0 || preview.archived_runs.length > 0) && (
            <button type="button" onClick={sweep} disabled={compact.isPending}
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-40">
              Sweep now
            </button>
          )}
        </div>
        {compact.error && <p className="text-sm text-red-600">{String(compact.error)}</p>}
      </div>
    </section>
  )
}
