# Field Team implementation

## RPG and motion update — November 1, 2026

Version 0.2 applies the approved cream/mint/dark-teal handheld RPG palette and menu frames to dashboard, detail drawers, and the native widget. Pixel portraits are displayed through clipped SVG viewports from the approved dashboard concept, retaining the source PNG. The desktop companion uses the generated eight-frame pixel Atlas/Pip atlas from the approved motion preview.

The native and browser transition trackers baseline each newly selected run. Initial existing requests retain their attention markers without replaying an alert. New request fingerprints or blocker transitions trigger one attention cue; completion triggers one celebration; new log events enter once. Repeated snapshots are quiet. Native idle blink and small working gestures loop, while alert and celebration poses are bounded. Pending attention takes precedence over completion. Reduce motion controls and OS settings suppress animation without hiding status information. Character levels remain metadata; XP progression is not fabricated.

Validation: the existing 31 Python tests pass, nine JavaScript transition scenarios pass, and thirteen Swift transition assertions pass. The native app was compiled, signed, and opened with pixel companion art and the RPG party panel. Dashboard layout and pixel portraits were inspected in the browser. Native multi-monitor dragging and long paid Claude runs remain outside this verification.

To run the additional motion checks:

```bash
node tests/motion-state.test.js
swiftc desktop/MotionState.swift tests/MotionTests.swift -o /tmp/field-team-motion-tests
/tmp/field-team-motion-tests
```

Field Team extends the workspace's updated `xsolla-orchestrate` skill. It leaves the older Run-Dex app and the original `orchestrate` installation unchanged. A user-approved symlink now installs this checkout as `~/.claude/skills/xsolla-orchestrate`. No Codex runtime, paid model calls, worker dispatch, publication, or deployment is part of this change.

## Delivered behavior

- Home shows the real main goal, task verification counts, recorded orchestrator identity, party goals, model/effort, current activity, statuses, and pending decisions.
- Agent detail drawers expose objectives, dependencies, routing reasons, critic/watchdog/acceptance evidence, recent agent events, and reports. The activity list links to full event text and can be filtered on Home.
- Party, Activity, Decisions, and Project memory navigation work without leaving the run. Saved HTML snapshots work offline with decision buttons disabled. Live views refresh every three seconds and disable decisions on connection loss.
- Approve and Deny in both surfaces share run-local records. Changed requests, duplicate responses, wrong runs, foreign origins, bad session tokens, worker-side writes, duplicate request IDs, and damaged decision JSON are rejected. No process control or requested action is executed by the API.
- Desktop companion uses original transparent trainer and creature art. Click opens the WebKit party panel, drag moves the pair, and menu controls select a run/project/skill, open Mission Control, switch to demo, or reduce motion. Idle animation respects macOS reduced motion.
- The companion starts a loopback-only dashboard server as needed and reuses a healthy server for that exact run. The server remains available after the app quits so an open browser can continue watching. Stop it using the run's recorded `dashboard.pid` when no longer needed.

## Metadata and source of truth

Task model and effort are read directly from the skill's routing data. Observed runtime model remains available in the collector; aliases are display labels, not model-access checks. The orchestrator is the supervising Claude conversation, not another spawned worker; fill its optional metadata from actual session values. Missing model/effort/status values are explicit instead of fabricated.

Creature species defaults by task role; it is independent of model choice. Optional task `character` metadata sets the chosen species, name, and level. No leveling/evolution rules were agreed during design, so levels are displayed only when recorded. Demo levels are labeled synthetic. Species do not grant permissions.

The recent event stream reads bounded tails of existing worker JSONL logs, plan updates, handoffs, and current-request decisions. It is not a new AI summarizer. Missing source timestamps stay missing. Hidden thinking is excluded. Reports are displayed as escaped text; project strings and logs cannot inject HTML or terminate the embedded script. The existing cost/status collector retains its original full-log parsing behavior.

## Build and validation

```bash
python3 scripts/build_view.py
python3 -m unittest discover -s tests -v
bash desktop/build.sh /absolute/path/to/output
```

The suite contains 31 tests, including the existing 19 runtime tests and 12 Field Team tests for data presentation, decision races, stale and cross-run requests, preserved history, bounded log ingestion, HTTP authorization, and offline script escaping. Tests use fixtures and no real model completions. HTTP tests require permission to bind loopback ports.

Validated October 30, 2026: native compilation and ad-hoc signing succeeded. Browser inspection confirmed the home layout, desktop breakpoint, and agent overview/activity drawer. The native app launched, clicking the companion opened Party, and the Needs you tab displayed the exact request with Approve and Deny. A synthetic approval from the native widget appeared in Mission Control with zero pending requests and “Approved · Awaiting Claude.” A synthetic dashboard denial produced “Denied · Awaiting revised plan” and no action execution. Screenshots are saved in the workspace outputs folder. Dragging, multi-monitor positioning, and prolonged live-run behavior have not been interactively verified.

Fonts use the existing Xsolla CDN and system fallbacks. The app is built for the local architecture and is not notarized. Live Claude account access and execution remain subject to the skill's separate pilot requirements.

## UX copy review

Audience: developers. Voice: direct, low brightness. Labels reviewed across meaning, narrative, consistency, common sense, and rules.

| Status | Elements | Copy | Issue | Fix |
|---|---|---|---|---|
| Pass | Navigation and sections | Home; Party; Activity; Approvals; Project memory; Main goal; Orchestrator; Your party; Needs your decision | None | — |
| Pass | Model metadata | Model; Effort; Not recorded; Lv. | Separates route, reasoning effort, and character level | — |
| Pass | Work summaries | Goal; Now; Working; Starting; Planned; Verified; Awaiting review; Awaiting approval; Blocked; Paused; Failed; Rejected | Matches recorded runtime state | — |
| Pass | Counts and times | Tasks verified; Working; Waiting for you; Pending; Updated; No update recorded; No time | No fabricated progress or timestamps | — |
| Pass | Details | View details; View full plan; View orchestrator; Assigned goal; Current activity; Task; Routing reason; Dependencies; Permitted writes; Critic; Watchdog; Acceptance; Done criteria; Overview; Activity; Report; Activity event | Links reveal the promised information | — |
| Pass | Decision actions | Approve; Deny; View request details; Full recorded request | Exact request is available in both surfaces | — |
| Pass | Decision results | Permission recorded; awaiting Claude update; No action executed; awaiting a revised plan | Approval is distinct from execution | — |
| Pass | Empty, demo, and connection states | Demo run; Synthetic activity; Saved snapshot; Connection lost; No decisions are waiting for you; No agents in this run; Create tasks in your Claude run to assemble a party | Explains current state and how to continue | — |
| Pass | Companion controls | Choose run or project; Choose xsolla-orchestrate folder; Demo mode; Refresh; Reduce motion; Open Mission Control; Quit Field Team | Explicit action labels | — |

## Artwork

`assets/field-team/characters.png` is an original transparent sprite atlas generated with the built-in ImageGen tool from the approved Claude-only concept board. Atlas, Pip, Rivet, and Aegis replace franchise artwork. Native and SVG viewports select atlas regions at runtime; the generated source image is preserved.

Generation prompt: “Production sprite atlas for approved Xsolla Field Team characters; transparent 2×2 grid, full-body Atlas trainer top left, Pip scout top right, Rivet builder bottom left, Aegis guardian bottom right; crisp smooth illustrated game sprites, dark teal/cyan uniform details, no text, UI, scenery, or existing franchise symbols.”
