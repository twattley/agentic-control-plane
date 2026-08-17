# Verification artifacts at the approval gate

## Identity

- `kind`: `epic`
- `epic_id`: `E003`

## Outcome

When a run reaches the human, the approval pane shows a **task-appropriate
verification artifact** so the owner verifies the *result*, not just the diff:
clickable dev URLs for UI changes, a real rendered data preview (head / summary
stats) for data work, a screenshot for visual change, a ready command for pure
backend logic. The artifact is **captured from actually running the code, never
composed by the agent** — the same "actual outputs, never claims" discipline the
plane already applies to builder evidence.

This closes the loop the plane is missing: today it hands the owner a diff,
green tests, and an Approve button, but never "go here to see it." The payoff of
a finished slice is being able to look at what it produced.

## Done When

- [ ] The `awaiting_human` / inbox pane renders a verification artifact inline,
      next to Approve.
- [ ] A UI slice yields clickable `http://localhost:<dev-port><route>` links
      derived from the run's changed routes, not guessed or hardcoded.
- [ ] A data slice yields a real captured preview (e.g. `head()` / row+null
      counts) rendered as HTML, produced by executing the code.
- [ ] Verification content is captured from a real run; a run with no observable
      surface says so honestly rather than fabricating one.

## Stories

- `E003-S00`
- `E003-S01`
