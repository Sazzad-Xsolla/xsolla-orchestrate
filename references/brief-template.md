# Worker brief template

Write to `RUN/workers/<id>/brief.md`. The worker sees **nothing else** from this conversation, so write it for a capable peer who just walked in. Be specific: paths, line ranges, names, commands.

```markdown
# Task <id>: <title>

## Goal
<One or two sentences: what this task achieves and why it matters to the overall goal.>

## Overall goal (context only, do not work on it)
<The run's restated goal, in one sentence, so the worker can sanity-check direction.>

## Background
- <Facts the worker needs: how the relevant code works, decisions already made, conventions to follow>
- <Pointers: `path/to/file.ts:120-180` does X; pattern to copy lives in `path/other.ts`>

## Already ruled out
- <Approaches or causes already checked and rejected, with the reason>

## Files
- May read: <paths or globs>
- **May write: <exact paths>. Writing anything else is a failure.**

## Done when
- [ ] <checkable criterion 1>
- [ ] <checkable criterion 2>

## Verify with
<exact command(s) to run from the project root, and what passing output looks like>

## Out of scope
- <things not to touch or "improve">

## If you get stuck
Stop and write `status: blocked` in your report, with the exact question. Don't guess.
```

Checklist before dispatching (then run `critique_brief.sh`, which checks most of this cold):
- [ ] Is every requirement the acceptance check tests stated in the brief? A hidden requirement guarantees a failed first attempt.
- [ ] Could someone with no chat history do this correctly the first time?
- [ ] Is every path real? (You checked it exists.)
- [ ] Did you **run** the `verify` command yourself from the project root? It must execute without network access or credentials, and any failure must be the real bug, not a missing tool.
- [ ] Does the brief contain no commit, push, post or other outward action?
- [ ] Does the "May write" list match `plan.json` → `writes`?
