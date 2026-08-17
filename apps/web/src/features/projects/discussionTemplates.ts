// Framework-free by design: this is the single source of truth for the
// "start from a template" feature. DiscussionPanel renders these field
// definitions and hands the filled-in values back to `compose` to build the
// opening message — no React, no API call, so correctness reads from the
// types and the one function body, not from a test suite.

export type TemplateKind = 'none' | 'bug' | 'feature'

/** Human-facing label for each picker option, in display order. */
export const TEMPLATE_KIND_LABELS: Record<TemplateKind, string> = {
  none: 'Blank',
  bug: 'Bug report',
  feature: 'Feature request',
}

export interface TemplateField {
  /** Key into the values map passed to `compose`. */
  key: string
  /** Rendered as the field's bold heading in the composed draft. */
  label: string
  /** Optional fields are omitted from the composed draft when left blank. */
  optional: boolean
  placeholder: string
}

const BUG_FIELDS: TemplateField[] = [
  {
    key: 'tryToDo',
    label: 'What I try to do',
    optional: false,
    placeholder: 'e.g. open the discussion panel and start a new ticket',
  },
  {
    key: 'actuallyHappens',
    label: 'What actually happens',
    optional: false,
    placeholder: 'e.g. the panel stays blank and nothing loads',
  },
  {
    key: 'shouldHappen',
    label: 'What should happen',
    optional: false,
    placeholder: 'e.g. the form should render with the skill dropdown',
  },
  {
    key: 'where',
    label: 'Where (app, page, area)',
    optional: false,
    placeholder: 'e.g. web app, project view, discussion panel',
  },
  {
    key: 'errorOrLogs',
    label: 'Error or logs',
    optional: true,
    placeholder: 'paste any error message or console output',
  },
]

const FEATURE_FIELDS: TemplateField[] = [
  {
    key: 'want',
    label: 'What I want',
    optional: false,
    placeholder: 'e.g. a way to start a discussion from a template',
  },
  {
    key: 'why',
    label: 'Why (what it unblocks)',
    optional: false,
    placeholder: 'e.g. saves retyping the same bug report structure every time',
  },
  {
    key: 'who',
    label: 'Who it\'s for',
    optional: false,
    placeholder: 'e.g. me, shaping tickets from the web UI',
  },
  {
    key: 'done',
    label: 'What "done" looks like',
    optional: false,
    placeholder: 'e.g. picking Bug renders fields that compose into the opening message',
  },
  {
    key: 'constraints',
    label: 'Constraints',
    optional: true,
    placeholder: 'e.g. no new dependency, no new API call',
  },
]

/** Field definitions for the templated kinds. `'none'` has no fields — the
 * raw draft is typed directly, so it isn't represented here. */
export const TEMPLATE_FIELDS: Record<Exclude<TemplateKind, 'none'>, TemplateField[]> = {
  bug: BUG_FIELDS,
  feature: FEATURE_FIELDS,
}

/** Values keyed by `TemplateField.key`. For `kind === 'none'`, the raw draft
 * text is read from the `raw` key instead. */
export type TemplateValues = Record<string, string>

/**
 * Turns filled-in field values into the opening message. Each populated
 * field becomes `**Label:** value`; optional fields left blank are omitted
 * entirely rather than emitted as an empty heading. `'none'` passes the raw
 * draft through unchanged — today's behavior, preserved as a real case
 * rather than a bypass around this function.
 */
export function compose(kind: TemplateKind, values: TemplateValues): string {
  if (kind === 'none') return values.raw ?? ''

  const headings: string[] = []
  for (const field of TEMPLATE_FIELDS[kind]) {
    const value = (values[field.key] ?? '').trim()
    if (value) headings.push(`**${field.label}:** ${value}`)
  }
  return headings.join('\n\n')
}
