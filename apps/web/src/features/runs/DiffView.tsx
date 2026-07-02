// Phone-friendly unified-diff renderer. Parses `git diff` into per-file,
// collapsible sections with +/- counts. No diff library — the git unified
// format is regular enough to split on `diff --git`.

interface FileDiff {
  path: string
  lines: string[]
  adds: number
  dels: number
}

function parseDiff(content: string): FileDiff[] {
  const files: FileDiff[] = []
  let current: FileDiff | null = null

  for (const line of content.replace(/\n$/, '').split('\n')) {
    if (line.startsWith('diff --git')) {
      // "diff --git a/foo b/foo" → prefer the b/ path
      const m = line.match(/ b\/(.+)$/)
      current = { path: m ? m[1] : line.slice(11), lines: [], adds: 0, dels: 0 }
      files.push(current)
      continue
    }
    if (!current) {
      // diff without a git header — treat the whole thing as one file
      current = { path: '(diff)', lines: [], adds: 0, dels: 0 }
      files.push(current)
    }
    current.lines.push(line)
    if (line.startsWith('+') && !line.startsWith('+++')) current.adds++
    else if (line.startsWith('-') && !line.startsWith('---')) current.dels++
  }
  return files
}

function lineClass(line: string): string {
  if (line.startsWith('+') && !line.startsWith('+++')) return 'bg-green-950/40 text-green-300'
  if (line.startsWith('-') && !line.startsWith('---')) return 'bg-red-950/40 text-red-300'
  if (line.startsWith('@@')) return 'text-cyan-400'
  return 'text-slate-400'
}

function FileSection({ file }: { file: FileDiff }) {
  const changes = file.adds + file.dels
  return (
    <details open={changes <= 60} className="min-w-0 overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
      <summary className="flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-xs">
        <span className="min-w-0 truncate font-mono text-slate-200">{file.path}</span>
        <span className="shrink-0 font-mono">
          <span className="text-green-400">+{file.adds}</span>{' '}
          <span className="text-red-400">−{file.dels}</span>
        </span>
      </summary>
      <pre className="overflow-x-auto border-t border-slate-800 px-3 py-2 text-xs leading-relaxed">
        <code>
          {file.lines.map((line, i) => (
            <div key={i} className={`whitespace-pre ${lineClass(line)}`}>{line || ' '}</div>
          ))}
        </code>
      </pre>
    </details>
  )
}

export function DiffView({ content }: { content: string }) {
  const files = parseDiff(content)
  const adds = files.reduce((n, f) => n + f.adds, 0)
  const dels = files.reduce((n, f) => n + f.dels, 0)

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">
        {files.length} file{files.length === 1 ? '' : 's'} ·{' '}
        <span className="text-green-600">+{adds}</span>{' '}
        <span className="text-red-600">−{dels}</span>
      </p>
      {files.map((f, i) => <FileSection key={i} file={f} />)}
    </div>
  )
}
