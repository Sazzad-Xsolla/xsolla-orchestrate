# Xsolla run view copy and design audit

Audience: internal developers and project owners. Voice brightness: low. The interface explains a Claude skill's run; it does not suggest that a standalone platform or autonomous approval system exists.

| Status | Element | Copy | Issue | Fix |
|---|---|---|---|---|
| Pass | Product label | Xsolla orchestrate | None | Keep |
| Pass | Context | AI orchestration; Claude Code skill | None | Keep |
| Pass | Navigation | Run overview; Tasks and agents; Agent communication; Project memory | None | Keep |
| Pass | Sidebar description | Your workflow stays in Claude. This optional view follows the local run. | None | Keep |
| Pass | Demo banner | Demonstration · Synthetic data · No live workers or model calls | None | Keep |
| Pass | Connection states | Connected to local run; Saved snapshot; Connection lost — showing last update | None | Keep |
| Pass | Fallback heading | Orchestration run | None | Keep |
| Pass | Empty goal | Define a goal in Claude to begin this run | None | Keep |
| Pass | Metrics | Verified progress; Active workers; Worker spend; Queued messages | None | Keep |
| Pass | Metric context | Up to 4 at once; No run checkpoint; Delivered at next dispatch | None | Keep |
| Pass | Task section | Tasks and agents; Assignments, model choices, and verification | None | Keep |
| Pass | Task context | Task worker; Waiting for dispatch | None | Keep |
| Pass | Disclosure | Inspect routing and checks | None | Keep |
| Pass | Routing labels | Routing reason; Dependencies; No reason recorded; None | None | Keep |
| Pass | Check labels | Critic review; Watchdog; Acceptance; Spend / task checkpoint | None | Keep |
| Pass | Check states | Not reviewed; No active signal; Passed; Failed; Not checked; Not recorded | None | Keep |
| Pass | Review heading | Needs your review | None | Keep |
| Pass | Review action | Copy review request | None | Keep |
| Pass | Review helper | Paste the request into your Claude conversation to review | None | Keep |
| Pass | Copy feedback | Copied — paste into your Claude conversation | None | Keep |
| Pass | Clipboard fallback | Ask Claude to review pending decisions for run … | None | Keep |
| Pass | Review empty state | No decisions are waiting for you | None | Keep |
| Pass | Activity section | Run activity | None | Keep |
| Pass | Activity empty state | Critic, watchdog, and coordination updates will appear as the run progresses | None | Keep |
| Pass | Task empty state | Tasks will appear after the orchestrator creates a plan | None | Keep |
| Pass | Communication description | Orchestrator-reviewed handoffs, delivered at checkpoints | None | Keep |
| Pass | Communication empty state | Agent handoffs will appear when the orchestrator forwards a finding or question | None | Keep |
| Pass | Evidence fallback | No evidence reference | None | Keep |
| Pass | Memory description | Approved lessons for future assignments | None | Keep |
| Pass | Memory context | Reviewed by …; Project context | None | Keep |
| Pass | Memory empty state | Reviewed lessons will appear after a verified task produces reusable project knowledge | None | Keep |
| Pass | Footer | Recorded decisions do not execute actions. Review consequential actions in Claude. | None | Keep |
| Pass | Dynamic record text | Run titles, goals, task titles, model aliases, statuses, messages, evidence, and reviewer names | Rendered as escaped text; source records determine wording | Keep |

The five-layer review covered meaning, flow, consistency, common sense, and writing rules. The page starts from the supplied Pentagram Dark template; button CSS and the official inline wordmark come from the supplied XUI references. Custom layout styles use declared tokens for color, spacing, radius, and shadows. Raw component dimensions remain verbatim from the component reference. Token references were checked programmatically. The rendered demo and expandable task details were inspected in the browser. Formal brand approval remains a pilot prerequisite.
