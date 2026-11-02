---
name: xsolla-orchestrate
description: Plan, route, critique, delegate, monitor, and verify Xsolla work, or resume an existing orchestration run. Includes a native Field Team mod pane.
---

Read `${CLAUDE_PLUGIN_ROOT}/SKILL.md` and follow its orchestration workflow. In that file, `SKILL` means `${CLAUDE_PLUGIN_ROOT}`, the plugin root containing `scripts/`, not this nested skill folder. Resolve this variable to an absolute path before running commands.

Use `/field-team` to open the native run pane. It follows the newest run in the current project; `/field-team /absolute/path/to/run` pins a specific run. The pane refreshes from the runtime records. Its Review in chat button fills a draft prompt; the user submits it to ask the supervising conversation to review pending requests. It grants no authorization and executes no actions.

The native pane works without starting the optional web dashboard or desktop companion. Continue using the runtime scripts for critique, dispatch, verification, and decisions.
