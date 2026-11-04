---
name: xsolla-orchestrate
description: Plan, route, critique, delegate, monitor, and verify Xsolla work, or resume an existing orchestration run. Includes a native Field Team mod pane.
---

Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` and follow its orchestration workflow. In that file, `SKILL` means `${CLAUDE_PLUGIN_ROOT}`, the plugin root containing `scripts/`, not this nested skill folder. Resolve this variable to an absolute path before running commands.

Before clarification, follow the root skill's startup steps: initialize/select the run in the intended project and run `python3 SKILL/scripts/start_views.py RUN` to open the desktop widget and dashboard pinned to its absolute path. Do not dispatch any critic or worker before the user confirms the concrete dispatch plan.

Use `/field-team /absolute/path/to/run` to open the native run pane pinned to the same run. The pane refreshes from the runtime records. Its Review in chat button fills a draft prompt; the user submits it to ask the supervising conversation to review pending requests. It grants no authorization and executes no actions.

Continue using the runtime scripts for critique, dispatch, verification, and decisions. Use the Bash/Python launchers for `claude -p` workers, including in automode; do not use native Agent/Task tools. Launch each ready independent group with `dispatch_wave.py RUN TASK_A TASK_B` before waiting for results or verifying either worker. A permission denial must be reported, not bypassed or replaced with silent serial execution.
