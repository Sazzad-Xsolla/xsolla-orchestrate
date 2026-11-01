# Routing

The executable policy is `config/routing.json`. Run `route.py RUN TASK` to explain a recommendation; add `--apply` to record it before critique. Account access requires a live pilot. The default routes are:

| Shape | Model | Effort | Checkpoint USD |
|---|---|---|---|
| lookup | sonnet | low | 1 |
| mechanical | sonnet | low | 1.5 |
| spec | sonnet | medium | 3 |
| tricky | sonnet | high | 4 |
| ambiguous | opus | high | 6 |
| review | opus | high | 4 |
| critic | sonnet | low | 0.5 |

High-risk lookup, mechanical, and specification tasks are raised to tricky. Specialist identity is independent of model choice. Deliberate overrides require a recorded routing_reason. Dispatch accepts only these model aliases and effort levels; add capabilities through deliberate tested changes. Do not overwrite an escalated route with the baseline recommendation.

## Checkpoints, not limits
A task's `budget_usd` is its **checkpoint**: roughly what the work should cost. It is not a limit, so a worker that genuinely needs more keeps going. Two things keep a worker from going off the rails, and neither is a dollar amount:

1. **The watchdog** (`scripts/watchdog.py`) runs beside every headless worker and checks its behaviour every 20 s. It pauses the worker when it sees any of these:

   | Signal | Means |
   |---|---|
   | `repeat_call` | The same command or file call 5 times in its last 20 calls |
   | `error_streak` | 8 tool errors in a row |
   | `guard_fights` | 3 blocked writes or denied commands |
   | `no_progress` | 40 turns since its last successful edit to its own files (tasks with a write list) |
   | `stall` | No output for 10 minutes |

   Pausing stops the process and keeps its files and session, so the worker can resume exactly where it was. The thresholds are at the top of `watchdog.py`.
2. **At the checkpoint** the worker ends with `error_max_budget_usd`. Run `escalate.py --cause budget`, which runs a health check:
   - **Healthy:** the checkpoint doubles and the worker resumes its session. This doesn't count as a failure and has no upper bound.
   - **Unhealthy (exit 6):** the worker is paused, and you ask the user.

The run budget (`run_budget_usd`, optional) is the only overall check-in. When spend reaches it, no new worker starts until the user says so. Running workers are never killed for it.

## Runtime boundary
This version dispatches headless workers only. Capture relevant conversation context in the brief; host-specific fork adapters are outside this implementation.

## Escalation ladder: escalate by cause
On a failed acceptance check, decide **why** it failed, then run `scripts/escalate.py --cause …`:

| Cause | Meaning | What changes | Session |
|---|---|---|---|
| `brief` | The brief left out or got wrong something the check needs | Correction goes into the brief; same tier | Resumed: the worker keeps its context |
| `capability` | The brief was clear and the work was still wrong | Effort goes up one notch, then the model; files are rolled back | Fresh |
| `budget` | It reached its checkpoint (`error_max_budget_usd`) | Health check first. Healthy: checkpoint doubled, same tier. Unhealthy: exit 6, treat as paused | Resumed; **not counted** |
| `environment` | A missing tool, a flaky service, or a wrong path in `verify` | You fix the environment first | Resumed; **not counted** |
| `resume` | The watchdog paused it and the user chose to let it continue | The user's guidance goes in as the gap | Resumed; **not counted** |

After 3 counted failures (`brief` + `capability`), or once the task is at the top tier, `escalate.py` exits 4. Stop and ask the user.

Identify the actual cause before escalating; more reasoning effort does not fix an environment or instruction problem.

## Tuning from history
Each finished task is recorded in `history.jsonl` by `record_outcome.py`. `python3 scripts/routing_report.py` shows the first-pass rate and cost per shape and tier, and suggests changes to this table. Offer the user any suggested edit; never change the table silently.
