import type { RunState } from '@agentic-control-plane/domain-types'

// Colour by who the state is waiting on: builder (amber), reviewer (violet),
// human (blue), terminal (slate/green/red).
const STYLES: Record<RunState, string> = {
  queued: 'bg-slate-100 text-slate-700',
  building: 'bg-amber-100 text-amber-800',
  awaiting_review: 'bg-violet-100 text-violet-800',
  reviewing: 'bg-violet-100 text-violet-800',
  needs_work: 'bg-amber-100 text-amber-800',
  fixing: 'bg-amber-100 text-amber-800',
  awaiting_human: 'bg-blue-100 text-blue-800',
  approved: 'bg-green-100 text-green-800',
  closing: 'bg-indigo-100 text-indigo-800',
  closed: 'bg-slate-200 text-slate-600',
  blocked: 'bg-red-100 text-red-800',
}

export function StateBadge({ state }: { state: RunState }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[state]}`}>
      {state.replace(/_/g, ' ')}
    </span>
  )
}
