# Specialist memory

Set a task's `specialist` to `implementation` or `review`. Profiles describe responsibility and capability, independently of model choice. Project lessons live in `.xsolla-orchestrator/memory.json`, separate from run records and from other projects.

After a task produces a useful lesson:

```bash
python3 SKILL/scripts/memory.py propose RUN impl implementation --text 'All exported event timestamps include a UTC offset' --evidence docs/events.md
python3 SKILL/scripts/memory.py list PROJECT
python3 SKILL/scripts/memory.py approve PROJECT MEMORY_ID --reviewer 'Project maintainer' --reason 'Checked against the implementation and passing acceptance evidence'
```

Approval requires the source task to be verified, its latest recorded acceptance result to pass, and the referenced evidence file to match its proposal-time digest. A lesson is not independently true just because those checks passed: the named reviewer must assess whether it generalizes. This is reviewed context, not model training or a credential system.

Dispatch includes at most the twelve most recent approved lessons for the selected specialist. Proposed and retired records are excluded. Approved lessons whose evidence changed or disappeared are treated as stale and excluded from dispatch context and the view until reviewed again. Use `memory.py retire PROJECT MEMORY_ID --reviewer NAME --reason REASON` to withdraw outdated knowledge, then propose its replacement. Do not retain credentials or sensitive excerpts unnecessarily.

For capability progression, use verified run outcomes as evidence of tasks a specialist has completed. There is no automatic leveling, permission expansion, or claim that the model itself learned. NN 2.0 integration is a later design review; this version makes no connection to it.
