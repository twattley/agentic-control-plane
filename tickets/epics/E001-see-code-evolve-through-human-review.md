# See code evolve through human review

## Identity

- `kind`: `epic`
- `epic_id`: `E001`

## Outcome

The owner can scroll a run from top to bottom and see how the code evolved at
the moments it came back for human review. Each reviewed agent-loop result is a
small checkpoint — one sentence and the code diff — with the owner's requested
change between checkpoints. Private builder/reviewer rounds remain available
to the control plane but do not leak into the human-facing story.

## Done When

- [ ] The first reviewed implementation appears as a one-line summary and its
      full diff from the run's starting point.
- [ ] Each later human-requested revision appears below the request as a
      one-line summary and only the incremental diff since the prior human
      checkpoint.
- [ ] Repeated requests form a chronological, downward-scrolling history of the
      conversation and code without showing internal agent traffic.

## Boundaries

- The run detail page is the human-facing surface; inbox and project summaries
  are separate work.
- Append-only events and internal review artifacts remain intact for the agent
  loop, diagnostics, and audit. This outcome changes their projection, not
  their retention.
- Retrospective reconstruction of incremental revisions for runs created
  before checkpoint data exists is not required; those runs fall back to one
  current result.

## Stories

- `E001-S00`
