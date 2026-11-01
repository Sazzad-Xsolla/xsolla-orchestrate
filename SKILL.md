---
name: xsolla-orchestrate
description: Coordinate multi-step work in Claude Code by planning tasks, choosing models and effort, critiquing briefs, delegating workers, reading logs, brokering agent handoffs, and verifying results. Use for Xsolla orchestration requests or to resume an existing Xsolla run.
---

# Xsolla orchestrate

Use the main Claude conversation as the orchestrator. The user stays in Claude; no additional account or application is needed. `SKILL` below is the absolute folder containing this file, not a fixed user installation path. `RUN` is an isolated run folder printed by `init_run.sh`.

## Before execution

1. Establish the goal, in/out scope, and observable acceptance criteria. Resolve questions that change what gets built. Honor choices and authorization already provided; do not ask for the same approval again.
2. Run `python3 SKILL/scripts/doctor.py` on first setup or after a runtime change. This checks local CLI flags, not authentication or model availability. Use only models the user's account can access; if a route is unavailable, report it and revise the routing policy deliberately.
3. Initialize a run: `bash SKILL/scripts/init_run.sh PROJECT SLUG [--template feature|bugfix|qa-access-pass] [--budget USD]`. Runs and project memory live under `PROJECT/.xsolla-orchestrator/`. Never reuse another installation's run folder.
4. Fill `RUN/plan.json`: goal, definition of done, verification plan, and tasks with unique IDs, write lists, dependencies, done criteria, and meaningful acceptance commands. Templates are drafts; replace all angle-bracket notes. Read [plan schema](references/plan-schema.md) for fields.
5. Route each task with `python3 SKILL/scripts/route.py RUN TASK --apply`. Read [routing](references/routing.md) for policy, overrides, and escalation. Record why any deliberate override is appropriate. Specialist identity is independent of model choice.
6. Write `RUN/workers/TASK/brief.md` using [the brief template](references/brief-template.md). Include the complete specification, concrete locations, permitted writes, verification, and dependencies. Optional `specialist` values are `implementation` or `review`; read the relevant `profiles/*.json` and approved memory when briefing.
7. Review the dispatch plan with the user if its scope, spending, or permissions are not already authorized. A run budget is optional. The task checkpoint is not a promise about total cost.

## Critique and dispatch

Run `bash SKILL/scripts/critique_brief.sh RUN TASK`. A fresh critic reads the brief before any worker is launched. Fix `needs-fixes` findings and repeat. Successful critique writes an audit bound to the brief and task configuration; changing either requires a new critique.

Run `python3 SKILL/scripts/dispatch.py RUN TASK --check` for a free preflight. Then launch `python3 SKILL/scripts/dispatch.py RUN TASK` with the host's supported background execution mechanism. Do not call `spawn_worker.sh` directly. Dispatch reserves slots under a lock, checks verified dependencies, rejects overlapping write ownership, and allows at most four active workers. A worker receives only its task brief, worker rules, relevant specialist memory, and messages addressed to it.

The optional headroom proxy reduces token usage. Without it, use `ORCH_ALLOW_UNWRAPPED=1` for an authorized run. The package does not start a proxy or rewrite user settings. Workers use tool restrictions and write hooks; these are operational guardrails, not an OS security sandbox. See [guardrails](references/guardrails.md).

## Monitor, coordinate, and recover

At worker exits and reasonable checkpoints, run `python3 SKILL/scripts/status.py RUN`. Read `STATUS.md`, worker reports, `stderr.txt`, and relevant `log.jsonl` events. Keep concise progress and required decisions in the conversation. The collector summarizes existing logs; it does not infer correctness from activity.

The watchdog observes repeated calls, error streaks, denied operations, lack of edits on writing tasks, and missing output. A paused worker needs review; explain the signal and obtain the user's direction before resuming. Read [routing](references/routing.md) for recovery by cause. The critic checks assignments; the watchdog checks execution signals; the orchestrator checks results.

Use [coordination](references/coordination.md) when agents need to exchange findings. Workers put proposed messages in their report; only the orchestrator forwards them:

```bash
python3 SKILL/scripts/coordinate.py RUN send --from impl --to review --kind finding --text 'The public interface accepts UTC timestamps' --evidence 'src/clock.py:24'
```

Messages are included at the next dispatch/resume checkpoint. They are not live injections and do not grant authority or change the task specification. For a critical mid-run change, pause dispatch of affected work and choose a controlled recovery; do not claim a running worker has received it. Consolidate repetitive conversations and bring unresolved disagreements back to the user.

## Verify and retain useful knowledge

Run `python3 SKILL/scripts/accept.py RUN TASK` yourself, inspect the relevant diff and evidence, and set the task to `verified` only after the criteria pass. Use `record_outcome.py RUN TASK verified` to retain routing outcomes. If acceptance fails, mark it `failed`, identify the cause, and use `escalate.py`; do not simply reroute an escalated task from scratch. Re-critique corrected briefs before redispatch.

Read [specialist memory](references/specialist-memory.md) when a result contains a reusable lesson. Propose a lesson with a source task and project evidence; approve it only after review. Saved memory supports future context, not model fine-tuning. Capability progression is evidence of verified work, never automatic permission expansion.

Workers propose consequential external actions in their report. Show the exact target and action to the user and obtain the required explicit authorization before the orchestrator executes them. No worker performs those actions. Recording a UI decision never executes an action or replaces required chat confirmation.

## Optional Field Team companion

The workflow is fully usable in Claude and `STATUS.md`. When requested, start `python3 SKILL/scripts/serve_dashboard.py RUN --theme xsolla` and share the printed localhost URL. Field Team shows the main goal, orchestrator, creature party, Claude models and efforts, live activity, agent details, and decisions. The optional macOS desktop companion is built with `bash SKILL/desktop/build.sh OUTPUT_DIRECTORY`; select the same run or project in its menu. It starts only the local view server, never workers. No hosted deployment is included.

Record the actual supervising identity in optional `plan.json.orchestrator` fields: `name`, `model`, `effort`, `status`, and `summary`. Keep the status and summary current at orchestration checkpoints. Do not invent a model, effort, heartbeat, or level for the view. Task `objective`, route, and worker logs supply agent goals and activity; optional `character` metadata supplies a display name, species (`pip`, `rivet`, `aegis`), and level. Character identity does not change model routing or permissions.

Dashboard and widget Approve/Deny controls write the same run-local `decisions.json`. Before acting, read this file and compare the recorded `fingerprint` against the current request with `field_team.fingerprint(RUN, approval)`. `decision: approve` records permission; `decision: reject` records denial. A changed request needs a new decision. UI responses do not execute actions, change worker state, resume paused workers, or replace required explicit chat confirmation. After performing an authorized action, update the approval's status through the existing locked plan writer so its execution is recorded separately.

## Close out or resume

Report each acceptance criterion with evidence, changes made, recorded cost, outstanding approvals, and anything unverified. Stop the optional view server using its recorded PID when no longer needed. Keep run records for resume and audit.

To resume, list runs with `bash SKILL/scripts/list_runs.sh PROJECT`, select the intended run, inspect plan, status, and logs, and continue from the recorded state. If the dispatch parent crashed, inspect worker PIDs before repairing a `dispatching` reservation; never start a duplicate worker automatically.
