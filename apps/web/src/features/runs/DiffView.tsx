// Minimal GitHub-style unified-diff renderer. Colours added/removed/hunk lines;
// good enough to eyeball a diff from a phone. No parsing library needed.

function lineClass(line: string): string {
  if (line.startsWith('+') && !line.startsWith('+++')) return 'bg-green-950/40 text-green-300'
  if (line.startsWith('-') && !line.startsWith('---')) return 'bg-red-950/40 text-red-300'
  if (line.startsWith('@@')) return 'text-cyan-400'
  if (line.startsWith('diff ') || line.startsWith('index ')) return 'text-slate-500'
  return 'text-slate-300'
}

export function DiffView({ content }: { content: string }) {
  const lines = content.replace(/\n$/, '').split('\n')
  return (
    <pre className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs leading-relaxed">
      <code>
        {lines.map((line, i) => (
          <div key={i} className={`whitespace-pre ${lineClass(line)}`}>
            {line || ' '}
          </div>
        ))}
      </code>
    </pre>
  )
}
