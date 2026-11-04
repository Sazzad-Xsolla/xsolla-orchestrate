---
name: xsolla-orchestrate
description: Coordinate multi-step work in Claude Code by planning tasks, choosing models and effort, critiquing briefs, delegating workers, reading logs, brokering agent handoffs, and verifying results. Use for Xsolla orchestration requests or to resume an existing Xsolla run.
---

# Xsolla orchestrate

Use the main Claude conversation as the orchestrator. The user stays in Claude; no additional account or application is needed. `SKILL` below is the absolute folder containing this file, not a fixed user installation path. `RUN` is an isolated run folder printed by `init_run.sh`.

Workers and brief critics run through the bundled Bash/Python launchers as separate `claude -p` processes. Do not use Claude's native Agent/Task subagent tools for this workflow, including in automode. Native subagent availability is not a prerequisite for this runtime. The supervising session must permit the launcher commands; if its permission mode denies them, report the denied command and stop dispatch. Do not change permission modes, disable safeguards, or silently replace parallel dispatch with serial work.

## Startup: open both views before clarification

1. Resolve `SKILL` and the intended `PROJECT` to absolute paths. Use the user's task folder, otherwise this chat's working directory. Never use the skill installation folder as the project. If the project itself is ambiguous, resolve only that location first.
2. For new work, immediately initialize an empty run with `bash SKILL/scripts/init_run.sh PROJECT SLUG`. This is local tracking setup, not permission to launch agents. Do not wait for clarification, routing, or approval to create it. For a resume, select the intended existing run instead.
3. Run `python3 SKILL/scripts/start_views.py RUN`. This starts/reuses the run's localhost dashboard, opens it, and opens the Field Team desktop widget pinned to that exact run and skill. It prints the resolved project, run, and dashboard URL; check all three. Do not use demo mode, a remembered folder, or “newest run” discovery. If startup fails, fix it or report the specific blocker before beginning clarification; do not silently skip either view.
4. Keep this same `RUN` throughout clarification, planning, and dispatch. Set its orchestrator status to `clarifying`, then `awaiting confirmation` when the plan is ready. Open the native `/field-team RUN` pane too when available; it does not replace the desktop widget and dashboard requested here.

## Clarify and prepare the dispatch plan

1. Establish the goal, in/out scope, and observable acceptance criteria. Resolve questions that change what gets built. Honor choices and authorization already provided; do not ask for the same approval again.
2. Run `python3 SKILL/scripts/doctor.py` on first setup or after a runtime change. This checks local CLI flags, not authentication or model availability. Use only models the user's account can access; if a route is unavailable, report it and revise the routing policy deliberately.
3. Use the run already opened at startup. Runs and project memory live under `PROJECT/.xsolla-orchestrator/`. Add any template tasks or optional budget to that run; do not initialize a second run after clarification.
4. Fill `RUN/plan.json`: goal, definition of done, verification plan, and tasks with unique IDs, write lists, dependencies, done criteria, and meaningful acceptance commands. Plan independent tasks with disjoint write ownership to run in parallel. Add `depends_on` only when a task actually needs another task's verified output; list order and a desire to verify one worker first are not dependencies. Templates are drafts; replace all angle-bracket notes. Read [plan schema](references/plan-schema.md) for fields.
5. Route each task with `python3 SKILL/scripts/route.py RUN TASK --apply`. Read [routing](references/routing.md) for policy, overrides, and escalation. Record why any deliberate override is appropriate. Specialist identity is independent of model choice.
6. Write `RUN/workers/TASK/brief.md` using [the brief template](references/brief-template.md). Include the complete specification, concrete locations, permitted writes, verification, and dependencies. Optional `specialist` values are `implementation` or `review`; read the relevant `profiles/*.json` and approved memory when briefing.
7. Show the goal, acceptance criteria, and dispatch table (task, model, effort, budget, writes, dependencies, acceptance command). **Wait for the user's explicit confirmation of this concrete plan before starting any agent, including the brief critic.** Invoking the skill or requesting the work is not confirmation of a plan the user has not seen. Honor an explicit confirmation already given for this exact plan; never infer it from silence or a UI opening. Only after that confirmation, record it with `python3 SKILL/scripts/dispatch_approval.py RUN approve --confirmation 'USER CONFIRMATION'`. The record is bound to the run, scope, routes, budgets, permissions, and acceptance checks. Changes to these require showing the revised plan and obtaining confirmation again. A run budget is optional. The task checkpoint is not a promise about total cost.

## Critique and dispatch

Identify the ready group: tasks whose dependencies are already verified, with disjoint writes, up to the four-worker capacity including workers already active. If two independent workers are ready, both belong in the next group. Show any genuine reason a planned task must wait.

Run `bash SKILL/scripts/critique_brief.sh RUN TASK` for every task in the ready group before dispatching the group. A fresh critic reads each brief. Fix `needs-fixes` findings and repeat. Successful critique writes an audit bound to the brief and task configuration; changing either requires a new critique. Critiques may run concurrently; completing one critique is not a reason to start and verify its worker before preparing the other ready tasks.

Preflight and launch the entire ready group with one command per step, substituting the actual task IDs:

```bash
python3 "SKILL/scripts/dispatch_wave.py" "RUN" task-a task-b --check
python3 "SKILL/scripts/dispatch_wave.py" "RUN" task-a task-b
```

Use the host's supported background Bash execution for the launch command (Claude Code: `run_in_background: true`) so the supervisor can monitor. The helper starts all listed dispatchers before waiting for any result, even if the host only offers foreground execution. Never launch task-a, wait for its result or acceptance, then launch independent task-b. Start the whole ready group before reading completion reports or running acceptance. For one ready task the same helper accepts one ID. Use `dispatch.py RUN TASK` only for deliberate single-task recovery, not a loop that waits on each independent task.

The group preflight checks capacity, dependencies, critiques, approval, and mutual write conflicts without starting workers. Each dispatcher then reserves its slot under a lock and rechecks the constraints; a concurrent change may still reject an individual launch. Check `RUN/workers/TASK/dispatch.log`, `meta.json`, and plan state to confirm actual workers started; a dispatcher PID alone is not proof. Report a launch failure rather than claiming parallel execution. Do not call `spawn_worker.sh` directly. At most four workers may be active. A worker receives only its task brief, worker rules, relevant specialist memory, and messages addressed to it.

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

After dispatching all ready workers, run `python3 SKILL/scripts/accept.py RUN TASK` yourself for completed tasks, inspect the relevant diff and evidence, and set the task to `verified` only after the criteria pass. Independent peers may keep running during task-specific review; wait for all relevant writers before a shared integration check. Verification unlocks real dependents, not independent peers that should already be running. Use `record_outcome.py RUN TASK verified` to retain routing outcomes. If acceptance fails, mark it `failed`, identify the cause, and use `escalate.py`; do not simply reroute an escalated task from scratch. Re-critique corrected briefs before redispatch.

Read [specialist memory](references/specialist-memory.md) when a result contains a reusable lesson. Propose a lesson with a source task and project evidence; approve it only after review. Saved memory supports future context, not model fine-tuning. Capability progression is evidence of verified work, never automatic permission expansion.

Workers propose consequential external actions in their report. Show the exact target and action to the user and obtain the required explicit authorization before the orchestrator executes them. No worker performs those actions. Recording a UI decision never executes an action or replaces required chat confirmation.

## Field Team views

When installed as a Claude Code plugin, `/field-team` opens the native mod pane with Party, Needs you, and Activity tabs. It follows this project's newest run; pass an absolute run path to pin one. The progress band and pane refresh from the runtime records. Review in chat fills a draft for the user to submit and does not record authorization or execute an action. The plugin skill entrypoint lives in `skills/xsolla-orchestrate/`; its `SKILL` path is the plugin root, where these scripts live.

The widget and localhost dashboard open at startup before clarification. Share the URL printed by `start_views.py`; keep both views pinned to `RUN`. The helper builds the macOS companion if needed, passes the absolute run and skill paths, and opens both views without launching agents. Field Team shows the main goal, orchestrator, creature party, models and efforts, live activity, agent details, and decisions. No hosted deployment is included.

Record the actual supervising identity in optional `plan.json.orchestrator` fields: `name`, `model`, `effort`, `status`, and `summary`. Keep the status and summary current at orchestration checkpoints. Do not invent a model, effort, heartbeat, or level for the view. Task `objective`, route, and worker logs supply agent goals and activity; optional `character` metadata supplies a display name, species (`pip`, `rivet`, `aegis`), and level. Character identity does not change model routing or permissions.

Dashboard and widget Approve/Deny controls write the same run-local `decisions.json`. Before acting, read this file and compare the recorded `fingerprint` against the current request with `field_team.fingerprint(RUN, approval)`. `decision: approve` records permission; `decision: reject` records denial. A changed request needs a new decision. UI responses do not execute actions, change worker state, resume paused workers, or replace required explicit chat confirmation. After performing an authorized action, update the approval's status through the existing locked plan writer so its execution is recorded separately.

## Close out or resume

Report each acceptance criterion with evidence, changes made, recorded cost, outstanding approvals, and anything unverified. Stop the optional view server using its recorded PID when no longer needed. Keep run records for resume and audit.

To resume, list runs with `bash SKILL/scripts/list_runs.sh PROJECT`, select the intended run, and open both views with `start_views.py RUN` before clarification or further dispatch. Inspect plan, status, and logs, then continue from the recorded state. A matching recorded dispatch confirmation may be reused; an absent or stale record requires explicit confirmation before launching any new agent. If the dispatch parent crashed, inspect worker PIDs before repairing a `dispatching` reservation; never start a duplicate worker automatically.
