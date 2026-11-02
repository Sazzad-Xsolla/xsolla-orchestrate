# Xsolla orchestrate

Source repository: [Sazzad-Xsolla/xsolla-orchestrate](https://github.com/Sazzad-Xsolla/xsolla-orchestrate).

A Claude Code orchestration skill with an optional Field Team interface. It plans and routes tasks, critiques briefs, monitors worker logs, brokers agent handoffs, and verifies results. Use the skill directly in Claude Code; Field Team provides an optional view of runs through a native pane, web dashboard, or macOS companion.

## Install the skill

Python 3.9+, Bash, Git, curl, and Claude Code are required for live execution. Model access and authentication use the existing Claude installation. Headroom is optional. No Python packages or frontend build step are required for the skill.

From this repository:

```bash
python3 scripts/doctor.py
python3 scripts/install.py --destination ~/.claude/skills/xsolla-orchestrate
```

The installer links this checkout under its own skill name and refuses to overwrite anything. Keep the checkout at its installed path. Invoke `/xsolla-orchestrate` in Claude Code and give it a scoped task. Existing skills and user configuration are unchanged. Use an explicit destination for another supported skills directory.

For live workers without the optional proxy, set `ORCH_ALLOW_UNWRAPPED=1` in the environment launching the orchestrator. The skill honors existing authorization but does not grant workers permission to publish, deploy, or message people.

## Everyday use in Claude Code

From the project you want to work on, launch `ORCH_ALLOW_UNWRAPPED=1 claude` if you are not using the optional Headroom proxy. The flag permits the skill to use Claude directly; it does not install or launch a proxy. Then invoke the skill with natural-language instructions:

```text
/xsolla-orchestrate Build the checkout flow. Keep changes local and verify them with tests.
/xsolla-orchestrate Show the current goal, party, progress, and anything that needs me.
/xsolla-orchestrate Resume the latest run in this project.
/xsolla-orchestrate Review the pending requests and explain the exact actions.
```

These are prompts for the skill, not separate fixed subcommands. The supervising Claude conversation plans, routes, critiques, dispatches, and verifies the work. The desktop app only observes runs and records permission decisions.

Useful terminal commands (replace `PROJECT` and `RUN` with actual paths):

```bash
python3 ~/.claude/skills/xsolla-orchestrate/scripts/doctor.py
bash ~/.claude/skills/xsolla-orchestrate/scripts/list_runs.sh PROJECT
python3 ~/.claude/skills/xsolla-orchestrate/scripts/status.py RUN
python3 ~/.claude/skills/xsolla-orchestrate/scripts/serve_dashboard.py RUN
```

In Field Team's menu choose **Choose run or project…**, then select the same project or a run under `.xsolla-orchestrator/`. Click the trainer for Party, Needs you, and Log. Approve/Deny records the decision; it never executes the requested action.

## Free demonstration

```bash
python3 scripts/demo.py --output /tmp/xsolla-orchestrate-demo
python3 scripts/serve_dashboard.py /tmp/xsolla-orchestrate-demo/.xsolla-orchestrator/demo --port 8792
```

The demonstration uses synthetic worker logs and exercises routing, handoff messages, review, memory approval, and memory reuse. It makes no model calls and never launches workers. The generated view explicitly labels the data as a demonstration.

## Develop and verify

```bash
python3 -m unittest discover -s tests -v
```

`SKILL.md` is the Claude entrypoint. Runtime code is in `scripts/`, routing policy in `config/routing.json`, specialist definitions in `profiles/`, and the optional view in `prototypes/xsolla-run.html`. The original runtime baseline and revision are recorded in `UPSTREAM.json`. Project records are isolated under `.xsolla-orchestrator/`.

## Working boundaries

Model routing chooses from the configured runtime aliases; the local doctor checks flags but cannot prove model access. Communication is delivered on dispatch or resume, not while an agent is already running. Memory is project-scoped and explicitly reviewed. Guard hooks and command restrictions are not a security sandbox: use an isolated environment for untrusted projects. Pause/recovery controls require the supervising Claude session.

The UI includes Xsolla design tokens and official brand artwork from the supplied design system. Fonts load from the Xsolla CDN with system fallbacks, so viewing the page may make font requests. No logs or project records are sent to that CDN. Brand review is still required before company rollout.

## Optional native Field Team interface

To use the skill with a native Field Team pane and a progress band above the prompt, load this checkout as a plugin. This optional installation path requires Claude Code 2.1.287 or later. From the project you want to work on:

```bash
ORCH_ALLOW_UNWRAPPED=1 claude --plugin-dir /absolute/path/to/xsolla-orchestrate
```

Use `/xsolla-orchestrate:xsolla-orchestrate` with your task to invoke the bundled skill. Use `/field-team` to open the native pane, or `/field-team /absolute/path/to/run` to select a run. With no argument it follows the newest run in the current project. The pane has Party, Needs you, and Activity tabs. It reads the same runtime state as the web dashboard, including verified progress, recorded spend, worker model/effort, and request fingerprints. Synthetic runs are labeled as demonstrations.

Interactive sessions refresh every five seconds and after a supervising turn. Refresh errors label the last snapshot as stale. Review in chat fills a draft for the user to submit; it neither approves nor executes a request. Run dispatch and acceptance continue through the bundled skill. The native interface does not need the separate web server or macOS app. Loading the plugin does not start workers or make model calls. Choose either this plugin installation or the standalone skill installation above to avoid duplicate skill listings.

Validate and test the optional plugin from this checkout:

```bash
claude plugin validate .
claude plugin test .
python3 -m unittest discover -s tests -v
```

Validated and tested with Claude Code 2.1.316. Native hook tests exercise terminal and desktop element trees; visual layout in an interactive Claude session still needs a pilot. The plugin has not been published to a marketplace. Directory submission checks report missing license, author, and icon metadata; choose these before publishing.

## Optional Field Team dashboard and desktop companion

The local run view now implements the approved Field Team layout: a goal and orchestrator summary, a creature party with Claude model/effort/goal/status, recent activity, agent details, and Approve/Deny controls. A browser and desktop widget watching the same run share decisions. Approvals record permission only; supervising Claude executes authorized actions separately.

```bash
python3 scripts/field_demo.py /tmp/field-team-demo
python3 scripts/serve_dashboard.py /tmp/field-team-demo/.xsolla-orchestrator/field-team-demo
bash desktop/build.sh /absolute/path/to/output
```

Open `Xsolla Field Team.app`, then use **Choose run or project…** in its menu. The app prefers this checkout and bundles a runtime fallback. First launch uses an explicitly synthetic demo. Selecting a project follows its newest `.xsolla-orchestrator` run. Drag the trainer to move it; click it to open Party, Needs you, and Log. Use **Choose xsolla-orchestrate folder…** to connect an updated checkout. Requires macOS 12+, Python 3 at `/usr/bin/python3`, and Xcode Command Line Tools for building. The local build is ad-hoc signed, not notarized.

See [Field Team implementation notes](docs/FIELD-TEAM.md) for metadata, decision semantics, validation, and limits. Legacy Run-Dex remains separate. Global skill installation is still explicit and uses the installer above.

Field Team 0.2 uses the approved cream-and-teal RPG style, pixel party portraits, and animated trainer/Pip poses. Idle blinks, working gestures, new-request alerts, completion celebrations, and log cues follow run events. Repeated polling does not replay notifications. The widget and dashboard offer Reduce motion, and macOS reduced motion is respected.

Field Team 0.3 refines this into the warm Xsolla field-journal design: parchment and sage surfaces, blue navigation, restrained cyan actions, unbranded character art, a dedicated Atlas portrait, and eight-frame companion gestures with longer quiet pauses. The other theme work is preserved separately under `theme-lab/`; a theme picker will be integrated later.

The November 2 motion revision replaces generated pose cycling with one stable drawing and subtle, continuous breathing anchored at the feet. Requests and completions use the existing envelope and notices; reduced motion keeps the drawing still. Earlier pose-animation descriptions above are historical.

Live model execution and account-specific compatibility require a pilot. See `docs/IMPLEMENTATION.md` for the delivery checklist and remaining work.
