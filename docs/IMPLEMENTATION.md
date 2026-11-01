# Implementation and pilot checklist

This checkout is the isolated Xsolla implementation. The original installation and its uncommitted changes were not modified. The repository is local; no GitHub repository, publication, deployment, or global installation is performed by the build.

## Implemented

- Dedicated skill name, installation target, run namespace, and project memory.
- Existing worker runtime, critic, watchdog, acceptance checks, snapshots, escalation, and outcome history.
- Explainable model/effort policy with risk-based routing.
- Dispatch preflight and locked worker reservations, dependency checks, ownership overlap checks, and current-brief critic fingerprints.
- Brokered checkpoint messages with bounded conversations and reply validation.
- Two specialist profiles with proposed, approved, and retired project lessons.
- Xsolla run view, synthetic demonstration, installation helper, and local environment checks.

## Pilot acceptance

1. Install into a fresh test account or explicit test destination and run the doctor.
2. Confirm authentication and the configured model aliases with an agreed small spend.
3. Execute a small implementation task plus a dependent review task; verify routing and acceptance evidence.
4. Change a brief and confirm dispatch requires a new critic review.
5. Send a handoff message and confirm the receiving worker uses it at its next dispatch.
6. Exercise a watchdog pause and user-directed recovery.
7. Propose a verified lesson, review it, then reuse it in a later run of the same project.
8. Confirm the Xsolla view and installation coexist with other skills.

## Build validation

Validated on October 29, 2026: 19 automated tests passed, including routing, current-brief critique, worker reservations, file ownership, checkpoint communication, reviewed memory, stale evidence exclusion, installation, and a fixture worker launch. The skill frontmatter validator passed. Python compilation, shell syntax, and XUI token checks passed. Browser inspection confirmed the rendered demo and expandable routing details; HTTP checks confirmed the data endpoint works and write requests receive status 405. The source bundle was extracted and its command entrypoint checked.

Model calls were replaced with fixture executables for automated runtime tests. No real model completion, model-access check, paid run, global skill installation, or publication was performed. The synthetic demo is explicitly labeled in the view.

## Remaining work before broader rollout

- Real model pilot and account-specific compatibility assessment.
- Design and brand review, including font distribution requirements.
- Anton review of existing NN 2.0 memory and agent capabilities before building an adapter.
- Longer-run validation of watchdog thresholds, log volume, process cleanup, and interrupted dispatch recovery.
- Specialist capability reporting based on verified outcomes; no automatic permission progression.
- Decisions about company repository ownership, licensing, distribution, and ongoing maintenance.

The current watcher remains heuristic. A stalled-output signal needs interpretation, and read-heavy work may need a different assignment shape. A crashed dispatch reservation is repaired manually after checking the actual process state. The run view is optional; it does not execute recorded approval requests.

## Field Team update — October 30, 2026

The optional view now implements Mission Control with the main goal, recorded orchestrator metadata, Claude-only party model/effort/goal/status, clickable agent details and logs, and shared Approve/Deny records. A macOS companion is included under `desktop/`. It starts the local view server, not workers. HTTP write requests are supported only for session-bound decision recording; other process/action endpoints remain unavailable. This supersedes the earlier read-only/HTTP-405 view validation above. All 31 tests passed. Native launch, Party, and demo approval synchronization were verified. See `FIELD-TEAM.md` for remaining limits and current installation details.
