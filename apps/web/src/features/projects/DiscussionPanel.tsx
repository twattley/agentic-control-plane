import type { DiscussionMessage } from '@agentic-control-plane/domain-types'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  useDiscussion, useDiscussions, useFreezeDiscussion,
  useSendDiscussionMessage, useStartDiscussion,
} from '../../api/hooks'

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

export function DiscussionPanel({ repoId, onClose }: { repoId: number; onClose: () => void }) {
  // Reopen the latest open discussion if one exists; otherwise start fresh.
  const { data: discussions } = useDiscussions(repoId)
  const latestOpen = discussions?.find((d) => d.state === 'open') ?? null
  const [startedId, setStartedId] = useState<number | null>(null)
  const discussionId = startedId ?? latestOpen?.id ?? null
  const { data: detail } = useDiscussion(repoId, discussionId)

  const start = useStartDiscussion(repoId)
  const send = useSendDiscussionMessage(repoId)
  const freeze = useFreezeDiscussion(repoId)

  const [draft, setDraft] = useState('')
  const [slug, setSlug] = useState('')
  const thinking = start.isPending || send.isPending || freeze.isPending

  const submit = () => {
    if (!draft.trim() || thinking) return
    if (discussionId === null) {
      start.mutate(draft, { onSuccess: (d) => { setStartedId(d.discussion.id); setDraft('') } })
    } else {
      send.mutate({ id: discussionId, message: draft }, { onSuccess: () => setDraft('') })
    }
  }

  const doFreeze = () => {
    if (discussionId === null || !slug.trim() || thinking) return
    freeze.mutate({ id: discussionId, slug: slug.trim() }, { onSuccess: onClose })
  }

  const error = start.error ?? send.error ?? freeze.error

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold text-slate-800">Shape an idea</h3>
        <button type="button" onClick={onClose} className="text-sm text-slate-400">close</button>
      </div>

      <div className="space-y-3">
        {detail?.messages.map((m) => <Message key={m.id} m={m} />)}
        {thinking && <p className="animate-pulse px-1 text-sm text-slate-400">thinking…</p>}
        {!detail?.messages.length && !thinking && (
          <p className="text-sm text-slate-400">
            Describe the idea — the agent reads this repo while you talk, then you freeze
            the result into a ticket.
          </p>
        )}
      </div>

      <div className="flex gap-2">
        <textarea rows={2} value={draft} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
          }}
          placeholder={discussionId === null ? 'What do you want to build?' : 'Reply…'}
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm" />
        <button type="button" onClick={submit} disabled={thinking || !draft.trim()}
          className="rounded-lg bg-slate-900 px-4 text-sm font-medium text-white disabled:opacity-40">
          Send
        </button>
      </div>

      {discussionId !== null && (
        <div className="flex gap-2 border-t border-slate-100 pt-3">
          <input value={slug} onChange={(e) => setSlug(e.target.value.trim())}
            placeholder="ticket id, e.g. TR-1"
            className="flex-1 rounded border border-slate-300 px-3 py-2 font-mono text-sm" />
          <button type="button" onClick={doFreeze} disabled={thinking || !slug.trim()}
            className="rounded-lg bg-blue-600 px-4 text-sm font-medium text-white disabled:opacity-40">
            {freeze.isPending ? 'freezing…' : 'Freeze ticket'}
          </button>
        </div>
      )}

      {error != null && <p className="text-sm text-red-600">{String(error)}</p>}
    </div>
  )
}
