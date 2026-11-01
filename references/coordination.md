# Agent coordination

Workers propose findings, questions, answers, and handoffs under `## Messages for peers` in their report. Include recipient task, text, and a concrete evidence reference. Do not directly edit another worker's files or inbox, and do not use Slack or external messaging for cross-talk.

The orchestrator reads the evidence, resolves permission or scope implications, then records a message:

```bash
python3 SKILL/scripts/coordinate.py RUN send --from impl --to review --kind finding --text 'The API rejects naive timestamps' --evidence 'src/time.py:28'
python3 SKILL/scripts/coordinate.py RUN list
```

Use `--reply-to MESSAGE_ID` for a reply between the same participants. The broker validates participants, caps text at 4000 characters, permits eight messages in each direction per pair and 200 per run, and atomically records updates under a lock. Summarize or escalate discussions that reach the limit.

`dispatch.py` includes messages addressed to the worker in `dispatch-context.json`, appended to the prompt even on resumed sessions. Queued messages become `included in dispatch`; that status does not prove worker acknowledgment. Previously included messages remain available when a worker resumes. No live delivery is claimed.

Critical findings about active work go back to the orchestrator. Avoid interrupting a healthy worker for routine updates. A changed assignment needs an updated brief, critic review, and a controlled resume. External actions still require the usual user approval.
