import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/** Markdown stays the source of truth — humans, agents and git all read it.
 * This renders the contract's known sections as UI so a story reads as a card
 * instead of a wall of text. Unknown sections fall through as prose. */

/** Sections written for the agent, not for the person deciding what to work
 * on. They are the contract the builder is held to — exact paths, commands,
 * interfaces — and they are noise when you are reading to understand the
 * problem. Kept one tap away, never deleted. */
const AGENT_SECTIONS = new Set([
  'scope', 'validation', 'public interface', 'scenarios', 'stories',
  'technical notes', 'evidence',
])

interface Section {
  heading: string
  body: string
}

function splitSections(markdown: string): Section[] {
  const sections: Section[] = []
  let heading = ''
  let lines: string[] = []
  let fenced = false

  for (const line of markdown.split('\n')) {
    if (line.trimStart().startsWith('```')) fenced = !fenced
    if (!fenced && line.startsWith('## ')) {
      sections.push({ heading, body: lines.join('\n') })
      heading = line.slice(3).trim()
      lines = []
      continue
    }
    lines.push(line)
  }
  sections.push({ heading, body: lines.join('\n') })
  return sections
}

/** `- [ ] text` / `- [x] text` lines, if this section is a checklist. */
function checklist(body: string): { done: boolean; text: string }[] {
  return body
    .split('\n')
    .map((line) => /^\s*-\s*\[( |x|X)\]\s*(.*)$/.exec(line))
    .filter((m): m is RegExpExecArray => m !== null)
    .map((m) => ({ done: m[1].toLowerCase() === 'x', text: m[2] }))
}

/** `- Key: value` lines from the Status block. */
function statusPairs(body: string): [string, string][] {
  return body
    .split('\n')
    .map((line) => /^\s*-\s*([A-Za-z ]+):\s*(.*)$/.exec(line))
    .filter((m): m is RegExpExecArray => m !== null && m[2].trim() !== '' && m[2].trim() !== '—')
    .map((m) => [m[1].trim(), m[2].trim()])
}

/** A word on what is inside a collapsed section, so it can be skipped without
 * being opened. */
function hint(name: string, body: string): string {
  if (name === 'scenarios') {
    const n = (body.match(/^###\s/gm) ?? []).length
    return n ? `${n} case${n === 1 ? '' : 's'}` : ''
  }
  if (name === 'scope') {
    const n = (body.match(/^\s+-\s/gm) ?? []).length
    return n ? `${n} path${n === 1 ? '' : 's'}` : ''
  }
  return ''
}

function Prose({ children }: { children: string }) {
  if (!children.trim()) return null
  return (
    // Sized down from prose-sm: a story is read on a phone, and the win is
    // fitting more of one on screen rather than comfortable long-form reading.
    <div
      className="prose prose-sm prose-slate max-w-none overflow-x-auto
        text-[13px] leading-snug
        prose-p:my-1.5 prose-p:text-[13px]
        prose-li:my-0.5 prose-li:text-[13px]
        prose-ul:my-1.5 prose-ol:my-1.5
        prose-headings:mb-1 prose-headings:mt-2.5 prose-headings:text-[13px]
        prose-pre:my-2 prose-pre:p-2 prose-pre:text-[12px]
        prose-code:text-[12px]
        prose-table:my-2 prose-th:py-1 prose-th:text-[12px]
        prose-td:py-1 prose-td:text-[12px]"
    >
      {/* GFM is what makes the evidence case table render as a table rather
        * than a run of pipe-delimited prose. */}
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  )
}

function SectionBlock({ section }: { section: Section }) {
  const name = section.heading.toLowerCase()

  // Identity is machine bookkeeping; the row header already shows the id.
  if (name === 'identity') return null

  if (name === 'status') {
    const pairs = statusPairs(section.body)
    if (!pairs.length) return null
    return (
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
        {pairs.map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-slate-400">{key}</dt>
            <dd className="text-slate-600">{value}</dd>
          </div>
        ))}
      </dl>
    )
  }

  const items = name.startsWith('done') ? checklist(section.body) : []
  if (items.length) {
    return (
      <div className="space-y-1">
        <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          {section.heading}
        </h4>
        {items.map((item) => (
          <div key={item.text} className="flex gap-2 text-[13px] leading-snug text-slate-700">
            <span className={item.done ? 'text-emerald-600' : 'text-slate-300'}>
              {item.done ? '☑' : '☐'}
            </span>
            <span className={item.done ? 'line-through decoration-slate-300' : ''}>
              {item.text}
            </span>
          </div>
        ))}
      </div>
    )
  }

  if (AGENT_SECTIONS.has(name)) {
    return (
      <details className="group rounded border border-slate-100 bg-slate-50/60">
        <summary className="cursor-pointer list-none px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 active:bg-slate-100">
          <span className="mr-1 inline-block group-open:rotate-90">▸</span>
          {section.heading}
          <span className="ml-1 font-normal normal-case tracking-normal text-slate-300">
            {hint(name, section.body)}
          </span>
        </summary>
        <div className="px-2 pb-2">
          <Prose>{section.body}</Prose>
        </div>
      </details>
    )
  }

  return (
    <div className="space-y-1">
      {section.heading && (
        <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          {section.heading}
        </h4>
      )}
      <Prose>{section.body}</Prose>
    </div>
  )
}

export function DocumentBody({ content }: { content: string }) {
  // Drop the leading `# Title` — the row header already shows it.
  const withoutTitle = content.replace(/^#\s+.*\n?/, '')
  return (
    <div className="space-y-2">
      {splitSections(withoutTitle).map((section, index) => (
        <SectionBlock key={`${section.heading}-${index}`} section={section} />
      ))}
    </div>
  )
}
