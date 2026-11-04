# plan.json

`init_run.sh` writes the skeleton. You keep this file current. The scripts read it, and some fields are written by scripts (marked *script*).

```json
{
  "run_id": "20261023-1430-checkout-refactor",
  "title": "Checkout Refactor",
  "project_dir": "/abs/path/to/project",
  "template": "feature",
  "goal": "One sentence the user agreed to.",
  "definition_of_done": [
    {"text": "Cart total uses Money type everywhere", "met": false, "evidence": ""}
  ],
  "verification_plan": "npm test && npm run typecheck",
  "run_budget_usd": 20,
  "dashboard": "local",
  "dispatch_confirmation": null,
  "dashboard_theme": "xsolla",
  "git_dirty_at_start": [],
  "tasks": [
    {
      "id": "t1",
      "title": "Use Money in cart totals",
      "shape": "spec",
      "objective": "…",
      "runtime": "headless",
      "model": "sonnet",
      "effort": "medium",
      "budget_usd": 3,
      "skills": false,
      "add_dirs": [],
      "writes": ["src/cart/total.ts", "src/cart/__tests__/"],
      "depends_on": [],
      "done_criteria": ["Totals are Money", "Rounding matches spec §4"],
      "accept": "npx vitest run src/cart && node .xsolla-orchestrator/<run>/acceptance/t1_rounding.mjs",
      "state": "planned",
      "attempt": 1,
      "resume_session": null,
      "routing_history": [],
      "accept_results": []
    }
  ],
  "approvals": [
    {"id": "a1", "from_task": "t1", "kind": "commit", "target": "branch feat/money",
     "text": "refactor(cart): use Money for totals", "status": "pending"}
  ],
  "log": [{"at": "14:40", "note": "t1 attempt 2 (brief): …"}]
}
```

| Field | Notes |
|---|---|
| `shape` | The routing row key (`lookup`, `mechanical`, `spec`, `tricky`, `ambiguous`, `review`). Feeds the routing history. |
| `writes` | Paths relative to `project_dir`, or absolute. A trailing `/` means a whole folder. **Enforced** by the write-guard hook, and snapshotted before each attempt. |
| `depends_on` | IDs of tasks whose verified output this task needs. Independent tasks use `[]` and launch together via `dispatch_wave.py`; task order and per-worker review do not create dependencies. |
| `accept` | Boss-only acceptance command, run from `project_dir`. Exit 0 means pass. Must test every done-criterion. |
| `skills` | `true` only if the worker must run one of the user's skills. That loads user settings and costs more at startup. |
| `add_dirs` | Extra folders the worker may access (for example a second repo). |
| `state` | `planned`, `running`, `verified`, `failed`, `blocked`, `paused` (the watchdog stopped it; files and session kept), `rejected`. `status.py` shows `awaiting review` for a finished, unchecked task. |
| `budget_usd` | The task's cost **checkpoint**, not a limit. Doubled automatically each time a healthy worker reaches it. |
| `resume_session` | *script* (`escalate.py`). The session a same-tier retry resumes. |
| `routing_history` | *script* (`escalate.py`). One entry per retry: cause, from/to tier, resumed, rolled back, gap. |
| `accept_results` | *script* (`accept.py`). One entry per acceptance run. |
| `approvals[].status` | `pending`, `executed`, `rejected`. Review and execute decisions through the supervising Claude conversation. |
| `dashboard` | `"local"` by default; widget and dashboard open before clarification. No hosted artifact copy. |
| `dispatch_confirmation` | Written by `dispatch_approval.py approve` only after explicit chat confirmation of the displayed goal and dispatch table. Fingerprinted to the run, project, scope, routing, spending, access, and acceptance checks. Missing/stale confirmation blocks critics and workers. Execution state and display changes do not invalidate it. |
| `specialist` | Optional `implementation` or `review`, independent of the model route. |
| `routing_reason` | Required explanation of the selected model and effort. |
| `risk` | `normal` or `high`; high-risk routine tasks receive a stronger baseline route. |
| `run_budget_usd` | `spawn_worker.sh` refuses to start a worker once total spend reaches it (exit 5). |
| `orchestrator` | Optional `{name, model, effort, status, summary}` for Field Team. Record actual Claude session values at checkpoints. Missing values display as not recorded. |
| `tasks[].character` | Optional `{species, name, level}`. Species: `pip`, `rivet`, or `aegis`. Display identity is independent of model/effort. Missing levels are omitted; the UI does not fabricate progression. |

Field Team writes UI responses separately in `RUN/decisions.json`, keyed by approval ID. Each response includes `decision` (`approve` or `reject`), `at`, `source`, and a `fingerprint` bound to the canonical request and resolved run path. Changed requests become pending again. Previous responses are retained when the same ID is revised. These responses are permission records, not execution records: `approvals[].status` remains pending until the supervisor records execution or rejection separately. Both dashboard and widget use the same plan-then-decisions lock order. Never interpret an approval as execution or resume a worker from a UI response.
