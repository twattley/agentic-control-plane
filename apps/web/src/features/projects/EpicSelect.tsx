import type { WorkflowEpic } from '@agentic-control-plane/domain-types'

/** The picker's sentinel for "no parent epic". The API models this as null. */
export const STANDALONE = ''

/** Picker value -> the API's nullable epic_id. */
export const parentForApi = (epicId: string): string | null => epicId || null

/** The parent picker shared by every authoring surface (new story, adopt,
 * freeze). Standalone is a first-class choice rather than a fallback: a repo
 * that has no epics yet must still be able to author real work, otherwise the
 * only place left for it is the legacy bucket. */
export function EpicSelect({
  value, onChange, epics,
}: { value: string; onChange: (epicId: string) => void; epics: WorkflowEpic[] }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="min-w-0 flex-1 rounded border border-slate-300 bg-white px-2 py-2 text-sm">
      {epics.map((epic) => (
        <option key={epic.epic_id} value={epic.epic_id}>
          {epic.epic_id} · {epic.title}
        </option>
      ))}
      <option value={STANDALONE}>Standalone — no epic</option>
    </select>
  )
}
