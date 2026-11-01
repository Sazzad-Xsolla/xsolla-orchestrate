# Guardrails

## Chain of command
User → you (orchestrator) → workers. Workers never ask the user anything and never act outward. You never act outward without the user's explicit yes in chat for that specific action.

## Headless workers: what is enforced
`spawn_worker.sh` launches `claude -p` with these layers:

| Layer | What it does |
|---|---|
| Allowlist + `--permission-mode acceptEdits` | Only Bash, Read, Edit, Write, Grep, Glob, NotebookEdit, WebFetch, WebSearch, TodoWrite, ToolSearch, Skill and headroom MCP are usable. Headless mode can't prompt, so everything else is denied. |
| `--disallowedTools` from `assets/deny.txt` | Blocks git history/remote commands, `gh`/`glab`, network tools (`curl`, `ssh`…), deploy and publish tools, destructive `rm`, `sudo`, `bash -c`/`sh -c`/`eval`, nested `claude`, and Agent. Every `Bash(...)` rule also gets an `rtk ` copy, because the user's rtk hook rewrites commands. |
| `assets/bin` shims first on `PATH` | `git` refuses commit/push/pull/fetch/merge/rebase/reset/checkout/switch/restore/clean/stash/tag/config/remote/worktree and similar. `gh`/`glab` refuse everything. Deny rules only see the outer command; in testing, `bash -c 'git commit'` slipped past them. The shims catch git however it is reached, including python `subprocess`. |
| Write-guard hook (`assets/hooks/guard_writes.py`, via `--settings`) | Every Edit/Write/MultiEdit/NotebookEdit outside the task's `writes` (plus its own worker folder for the report) is refused at the moment it's tried. |
| `--strict-mcp-config` (headroom only) | Slack, Gmail, Jira, Confluence, Drive, Calendar and Neuronet aren't loaded for workers. You do the lookups and put the results in the brief. |
| `--setting-sources project,local` (unless `skills: true`) | The user's global hooks and settings don't load in workers. That makes startup cheaper and behavior more predictable. |
| Watchdog (`scripts/watchdog.py --follow`, started with every worker) | Pauses a worker that loops, keeps erroring, fights its guardrails, stops making progress, or hangs. Its files and session are kept. |
| `--max-budget-usd` per task (a checkpoint), `run_budget_usd` per run (optional) | At the checkpoint, a healthy worker is resumed with double the checkpoint. Only the watchdog's verdict can hold it back, not spend. `spawn_worker.sh` won't start new workers past the run budget without the user's yes. |
| Snapshots | `spawn_worker.sh` saves the write-list files before each attempt. `snapshot.py restore` puts them back. |

**These layers are defense in depth for a cooperative worker, not a sandbox.**
- Bash can still write files through redirects, which the write guard doesn't see. Drift detection in `status.py` catches those afterwards.
- Python can reach the network.
- `/usr/bin/git` bypasses the shim.

That's why every result gets a boss review with `git status`, `git log` and the acceptance check. If a commit or other change appears that nobody approved, stop the run and tell the user.

## Fork workers (outside this runtime)
The current Xsolla dispatch runtime supports headless workers only. Do not select fork as a route. The following upstream considerations apply only if a future host adapter explicitly adds fork support.

### Upstream considerations
A fork inherits your tools, including the ones that post and send. The guardrails hold only because its prompt says so. To keep that safe:
- Get the user's yes before using a fork. Paste the full `assets/worker-rules.md` into its prompt.
- Tell it to return its report as its final message, because the harness blocks subagents from writing report files. Tell it to leave the session, task-list and wrap-up tools alone.
- After it finishes, check `git status` and `git log`, and look for any outward action it might have taken.

## Proposed-action flow
1. A worker writes the action in its report with the kind, the target and the exact text.
2. You copy it to `plan.json` → `approvals` with `status: pending`. It appears in STATUS.md and on the dashboard, and `status.py` raises a NOTIFY.
3. Review the exact action and target in Claude and collect the required explicit authorization. The optional run view is read-only and never executes actions.
4. On a chat yes, you execute it and set `status: executed`.

## Things you also never do without asking
- Merge branches, delete branches, force-push, or rewrite history.
- Change `~/.claude.json`, `~/.claude/settings*.json`, or project `.claude/` settings.
- Start a paid or long-running external job, or exceed the run budget.
