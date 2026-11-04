# Xsolla Orchestrate

**Plan, run, and verify parallel Claude Code workers from one conversation.**

Xsolla Orchestrate turns a scoped task into an execution plan, assigns models and effort, reviews worker briefs, and launches independent workers in parallel. The supervising Claude conversation coordinates the work and verifies each result. Field Team provides a native Claude pane, a local dashboard, and a macOS desktop companion for following progress.

[Quick start](#quick-start) · [How it works](#how-it-works) · [Field Team](#field-team) · [Development](#development) · [Limitations](#limitations)

## Capabilities

| Capability | Behavior |
| --- | --- |
| Parallel execution | Launch up to four independent workers together; dependent tasks wait for verified output. |
| Model routing | Choose a configured model and effort for each task, with recorded routing and recovery decisions. |
| Brief review | Review instructions before launch and invalidate the review when relevant inputs change. |
| Monitoring | Collect worker logs, reports, recorded spend, and watchdog signals. |
| Verification | Run acceptance checks and inspect evidence before marking a task verified. |
| Continuity | Retain run records, reviewed specialist memory, and handoff messages for later dispatch or resume. |
| Field Team | Follow goals, assignments, progress, and pending decisions from the same run records. |

## Requirements

- Claude Code with an authenticated account and access to the configured worker models.
- Python 3.9+, Bash, Git, and curl.
- macOS 12+ and Xcode Command Line Tools for building the desktop companion used by the default startup workflow.
- Optional: a running Headroom proxy for token compression.

The core Python runtime requires no third-party Python packages or frontend build step. Live workers use your Claude account and incur model usage charges. The local doctor checks CLI capabilities; it cannot verify authentication or model access.

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/Sazzad-Xsolla/xsolla-orchestrate.git
cd xsolla-orchestrate
python3 scripts/doctor.py
python3 scripts/install.py --destination ~/.claude/skills/xsolla-orchestrate
```

The installer links this checkout into your skills directory and refuses to overwrite an existing installation. Keep the checkout at this location after installation.

### 2. Open your project in Claude Code

```bash
cd /absolute/path/to/your-project
ORCH_ALLOW_UNWRAPPED=1 claude
```

`ORCH_ALLOW_UNWRAPPED=1` permits workers to run directly when Headroom is unavailable. If you use Headroom, start its proxy through your usual setup before launching the run. The skill does not start or configure the proxy.

### 3. Describe the work

```text
/xsolla-orchestrate Build the checkout flow. Keep changes local and verify them with tests.
```

Start from the actual project directory. If you launch from a parent directory containing several projects, Claude needs to identify the intended project first.

The skill creates a run, opens the dashboard and desktop widget, and prepares a dispatch plan. Review the goal, acceptance criteria, assignments, model routes, and spending checkpoints. Critics and workers launch after you confirm that concrete plan.

Other example requests:

```text
/xsolla-orchestrate Show the current goal, worker progress, and anything that needs me.
/xsolla-orchestrate Resume the latest run in this project.
/xsolla-orchestrate Review the pending requests and explain the exact actions.
```

These are natural-language requests, not fixed CLI subcommands.

## How it works

1. **Prepare.** Select the project, create or resume an isolated run, and open its Field Team views.
2. **Plan.** Define task ownership, dependencies, acceptance checks, model routes, and worker briefs.
3. **Confirm and critique.** Obtain confirmation of the dispatch plan, then review each brief.
4. **Dispatch in parallel.** Start the ready group of independent workers before waiting for any worker's result.
5. **Monitor and coordinate.** Review logs, watchdog signals, reports, and proposed handoffs.
6. **Verify.** Run acceptance checks, inspect the changes, and record verified outcomes before unlocking dependent tasks.

Workers run as separate `claude -p` processes through the bundled Bash/Python launchers. This workflow uses CLI workers in automode and does not require native Agent/Task subagent tools. The supervising session must still permit the launcher commands; a permission denial stops dispatch.

The group launcher checks approval, brief reviews, capacity, dependencies, and file ownership before starting dispatchers. Run from the checkout with actual run paths and task IDs:

```bash
python3 scripts/dispatch_wave.py /absolute/path/to/run task-a task-b --check
python3 scripts/dispatch_wave.py /absolute/path/to/run task-a task-b
```

Independent tasks use disjoint write lists. Tasks requiring another task's output wait until that dependency is verified. Each dispatcher rechecks the constraints and reserves its slot under a lock.

Run records live in the target project's `.xsolla-orchestrator/` directory. To inspect existing runs:

```bash
bash ~/.claude/skills/xsolla-orchestrate/scripts/list_runs.sh /absolute/path/to/project
python3 ~/.claude/skills/xsolla-orchestrate/scripts/status.py /absolute/path/to/run
```

## Field Team

Field Team displays the goal, worker assignments, models and effort, recorded spend, recent activity, and pending decisions. Approve/Deny controls record decisions; the supervising conversation reviews and executes authorized actions separately.

### Dashboard and macOS companion

The default skill workflow opens both views and pins them to the selected run. In the desktop companion, use **Choose run or project…** to inspect another run. Click the trainer to open the party, pending requests, and activity log; drag it to reposition the widget.

For manual dashboard startup or a desktop build, run from the checkout:

```bash
python3 scripts/serve_dashboard.py /absolute/path/to/run
bash desktop/build.sh /absolute/path/to/output
```

The companion supports reduced motion. Local builds are ad-hoc signed and are not notarized. See [Field Team implementation notes](docs/FIELD-TEAM.md) for view behavior, decision handling, and platform details.

### Native Claude Code pane

To load the native pane and progress band, use the checkout as a Claude Code plugin. This integration requires Claude Code 2.1.287 or later.

```bash
cd /absolute/path/to/your-project
ORCH_ALLOW_UNWRAPPED=1 claude --plugin-dir /absolute/path/to/xsolla-orchestrate
```

Invoke `/xsolla-orchestrate:xsolla-orchestrate` with your task. Use `/field-team` to follow the project's newest run, or `/field-team /absolute/path/to/run` to select a specific run. The pane has Party, Needs you, and Activity tabs. **Review in chat** prepares a draft for you to submit to the supervising conversation.

Choose either the standalone skill installation or the plugin loading method to avoid duplicate skill listings. The native pane itself does not require the dashboard or macOS app; the skill's default workflow still opens both views. Loading the plugin alone does not start workers.

## Try a demonstration

From the checkout:

```bash
python3 scripts/demo.py --output /tmp/xsolla-orchestrate-demo
python3 scripts/serve_dashboard.py /tmp/xsolla-orchestrate-demo/.xsolla-orchestrator/demo --port 8792
```

The demonstration uses synthetic records to show routing, handoffs, review, and specialist memory. It makes no model calls, launches no workers, and labels its data as a demonstration.

## Development

Run the Python test suite from the checkout:

```bash
python3 -m unittest discover -s tests -v
```

For the native plugin, also run:

```bash
claude plugin validate .
claude plugin test .
```

| Location | Purpose |
| --- | --- |
| [SKILL.md](SKILL.md) | Supervising workflow and execution rules |
| [scripts/](scripts/) | Dispatch, monitoring, acceptance, and run management |
| [config/routing.json](config/routing.json) | Model routing policy |
| [profiles/](profiles/) | Specialist definitions |
| [skills/xsolla-orchestrate/](skills/xsolla-orchestrate/) | Claude Code plugin skill entrypoint |
| [desktop/](desktop/) | macOS companion source and build tooling |
| [tests/](tests/) | Runtime and integration tests |

See [the implementation checklist](docs/IMPLEMENTATION.md) for validation coverage and remaining work, and [UPSTREAM.json](UPSTREAM.json) for the original runtime baseline.

## Limitations

- **Live compatibility needs a pilot.** Account-specific model access and live automode execution require validation in your Claude environment. Parallel dispatch has automated coverage using fixture workers.
- **Worker restrictions are not an OS sandbox.** Tool restrictions, command shims, write hooks, snapshots, and watchdogs provide operational controls. Use an isolated environment for untrusted projects. See [guardrails](references/guardrails.md).
- **Handoffs arrive at checkpoints.** Messages are delivered on dispatch or resume; they are not injected into an active worker. Specialist memory is scoped to the project and explicitly reviewed.
- **External actions remain supervised.** Workers propose consequential actions in reports. Publishing, deploying, messaging, and other actions requiring authorization are handled by the supervising conversation after approval.
- **Distribution is local.** The plugin has not been published to a marketplace. License, author, and icon metadata still need review before directory submission.
- **Brand review is pending.** The interface uses Xsolla design resources and CDN-hosted fonts with system fallbacks. Font loading may make CDN requests; project records and logs are not sent to that CDN. Company rollout requires brand review.
