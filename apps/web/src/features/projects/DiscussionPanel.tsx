import type {
  CoordinationClass, DiscussionMessage, WorkflowEpic,
} from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  useDiscussion, useDiscussions, useDiscussionSkills, useFreezeDiscussion,
  useSendDiscussionMessage, useStartDiscussion,
} from '../../api/hooks'
import { EpicSelect, STANDALONE } from './EpicSelect'
import {
  compose, TEMPLATE_FIELDS, TEMPLATE_KIND_LABELS, type TemplateKind, type TemplateValues,
} from './discussionTemplates'

const CLASSES: CoordinationClass[] = ['feature', 'contract', 'platform', 'validation']

function Message({ m }: { m: DiscussionMessage }) {
  if (m.role === 'human') {
    return (
      <div className="ml-8 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-800">
        {m.content}
      </div>
    )
  }
  return (
    <div className="prose prose-sm prose-slate mr-4 max-w-none overflow-x-auto px-1">
      <ReactMarkdown>{m.content}</ReactMarkdown>
    </div>
  )
}

function ThinkingIndicator() {
  return (
    <div role="status" aria-live="polite"
      className="flex items-center gap-2 px-1 text-sm text-slate-400">
      <span>Agent is thinking</span>
      <span aria-hidden="true" className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:300ms]" />
      </span>
    </div>
  )
}

export function DiscussionPanel({
  repoId, onClose, epics, ticketContract,
}: {
  repoId: number
  onClose: () => void
  epics?: WorkflowEpic[]
  ticketContract?: string | null
}) {
  // "New ticket" means a new one. Auto-reopening the newest open discussion
  // made every visit land back in the last conversation with no way past it —
  // and a discussion only closes when you freeze it, so shaping a ticket any
  // other way left one open forever. Resuming is now something you choose.
  const { data: discussions } = useDiscussions(repoId)
  const skills = useDiscussionSkills(repoId)
  const latestOpen = discussions?.find((d) => d.state === 'open') ?? null
  const [startedId, setStartedId] = useState<number | null>(null)
  const [resumedId, setResumedId] = useState<number | null>(null)
  const discussionId = startedId ?? resumedId ?? null
  const { data: detail } = useDiscussion(repoId, discussionId)

  const start = useStartDiscussion(repoId)
  const send = useSendDiscussionMessage(repoId)
  const freeze = useFreezeDiscussion(repoId)

  // The draft is derived rather than typed directly so that picking a
  // template and typing plain text share one code path through `compose` —
  // 'none' just passes the `raw` value through unchanged.
  const [templateKind, setTemplateKind] = useState<TemplateKind>('none')
  const [templateValues, setTemplateValues] = useState<TemplateValues>({})
  const draft = compose(templateKind, templateValues)
  const setRaw = (value: string) => setTemplateValues((v) => ({ ...v, raw: value }))
  const setField = (key: string, value: string) => (
    setTemplateValues((v) => ({ ...v, [key]: value }))
  )
  const [skillName, setSkillName] = useState('')
  const [slug, setSlug] = useState('')
  const [epicId, setEpicId] = useState(epics?.[0]?.epic_id ?? STANDALONE)
  const [klass, setKlass] = useState<CoordinationClass>('feature')
  // Driven by the repo's contract, NOT by whether epics exist. A contract repo
  // with no epics yet still freezes into a story (standalone) — deciding on
  // epic count silently dropped that work into the legacy flat-ticket branch.
  const contractMode = ticketContract === 'epic-story-v1'
  const sending = start.isPending || send.isPending
  const busy = sending || freeze.isPending

  const submit = () => {
    if (!draft.trim() || busy) return
    if (discussionId === null) {
      start.mutate(
        { message: draft, ...(skillName ? { skill_name: skillName } : {}) },
        {
          onSuccess: (d) => {
            setStartedId(d.discussion.id)
            setTemplateKind('none')
            setTemplateValues({})
          },
        },
      )
    } else {
      send.mutate({ id: discussionId, message: draft }, { onSuccess: () => setRaw('') })
    }
  }

  const doFreeze = () => {
    if (discussionId === null || busy) return
    if (contractMode) {
      // Exactly one parent mode — the API rejects both together.
      freeze.mutate(
        {
          id: discussionId, coordination_class: klass,
          ...(epicId ? { epic_id: epicId } : { standalone: true }),
        },
        { onSuccess: onClose },
      )
    } else {
      if (!slug.trim()) return
      freeze.mutate({ id: discussionId, slug: slug.trim() }, { onSuccess: onClose })
    }
  }

  const error = skills.error ?? start.error ?? send.error ?? freeze.error

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold text-slate-800">
          {discussionId === null ? 'New ticket' : 'Editing draft'}
        </h3>
        <button type="button" onClick={onClose} className="text-sm text-slate-400">close</button>
      </div>

      {discussionId === null ? (
        <>
          <label className="block space-y-1 text-sm text-slate-600">
            <span>Shaping method</span>
            <select value={skillName} onChange={(e) => setSkillName(e.target.value)}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="">Plain conversation</option>
              {skills.data?.map((skill) => (
                <option key={skill.name} value={skill.name}>
                  {skill.name} — {skill.description}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1 text-sm text-slate-600">
            <span>Start from</span>
            <select value={templateKind}
              onChange={(e) => {
                setTemplateKind(e.target.value as TemplateKind)
                setTemplateValues({})
              }}
              className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm">
              {(Object.entries(TEMPLATE_KIND_LABELS) as [TemplateKind, string][]).map(
                ([kind, label]) => <option key={kind} value={kind}>{label}</option>,
              )}
            </select>
          </label>
          {templateKind !== 'none' && (
            <div className="space-y-2 rounded border border-slate-200 bg-slate-50 p-3">
              {TEMPLATE_FIELDS[templateKind].map((field) => (
                <label key={field.key} className="block space-y-1 text-sm text-slate-600">
                  <span>{field.label}{field.optional ? ' (optional)' : ''}</span>
                  <textarea rows={1} value={templateValues[field.key] ?? ''}
                    onChange={(e) => setField(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
                </label>
              ))}
            </div>
          )}
        </>
      ) : detail?.discussion.skill_name ? (
        <p className="text-xs text-slate-400">
          Shaping with {detail.discussion.skill_name}
        </p>
      ) : null}

      <div aria-busy={sending} className="space-y-3">
        {detail?.messages.map((m) => <Message key={m.id} m={m} />)}
        {sending && <ThinkingIndicator />}
        {!detail?.messages.length && !sending && (
          <p className="text-sm text-slate-400">
            Describe the idea — the agent reads this repo while you talk. Nothing is
            written until you hit Create ticket.
          </p>
        )}
      </div>

      {discussionId === null && latestOpen !== null && (
        <button type="button"
          onClick={() => {
            setResumedId(latestOpen.id)
            // The picker only applies to starting a new discussion — an
            // in-flight template selection must not leak into the resumed
            // reply box.
            setTemplateKind('none')
          }}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-left text-sm text-slate-500">
          Carry on with the unfinished draft from{' '}
          {new Date(latestOpen.updated_at).toLocaleDateString()} instead
        </button>
      )}

      <div className="flex gap-2">
        {discussionId === null && templateKind !== 'none' ? (
          <div className="flex-1 whitespace-pre-wrap rounded border border-dashed
            border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-500">
            {draft || 'Fill in the fields above to compose the opening message.'}
          </div>
        ) : (
          <textarea rows={2} value={draft} onChange={(e) => setRaw(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
            }}
            placeholder={discussionId === null ? 'What do you want to build?' : 'Reply…'}
            className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm" />
        )}
        <button type="button" onClick={submit} disabled={busy || !draft.trim()}
          className="min-w-24 rounded-lg bg-slate-900 px-4 text-sm font-medium text-white disabled:opacity-40">
          {sending ? 'Thinking…' : 'Send'}
        </button>
      </div>

      {discussionId !== null && (
        <div className="flex gap-2 border-t border-slate-100 pt-3">
          {contractMode ? (
            <>
              <EpicSelect value={epicId} onChange={setEpicId} epics={epics ?? []} />
              <select value={klass}
                onChange={(e) => setKlass(e.target.value as CoordinationClass)}
                className="rounded border border-slate-300 bg-white px-2 py-2 text-sm">
                {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </>
          ) : (
            <input value={slug} onChange={(e) => setSlug(e.target.value.trim())}
              placeholder="ticket id, e.g. TR-1"
              className="flex-1 rounded border border-slate-300 px-3 py-2 font-mono text-sm" />
          )}
          <button type="button" onClick={doFreeze}
            disabled={busy || (!contractMode && !slug.trim())}
            className="rounded-lg bg-blue-600 px-4 text-sm font-medium text-white disabled:opacity-40">
            {freeze.isPending ? 'creating…' : 'Create ticket'}
          </button>
        </div>
      )}

      {error != null && <p className="text-sm text-red-600">{String(error)}</p>}
    </div>
  )
}
