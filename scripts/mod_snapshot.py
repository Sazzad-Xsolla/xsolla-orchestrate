"""Read existing run records for the Claude Code mod; never launch workers."""

import argparse
import json
from pathlib import Path

from status import collect


def resolve_run(target):
    target = Path(target).expanduser().resolve()
    if (target / 'plan.json').is_file():
        return target
    runs = target if target.name == '.xsolla-orchestrator' else target / '.xsolla-orchestrator'
    candidates = [p for p in runs.iterdir() if p.is_dir() and (p / 'plan.json').is_file()] if runs.is_dir() else []
    return max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name)) if candidates else None


def snapshot(target):
    run = resolve_run(target)
    if run is None:
        return {'run': None, 'message': 'No orchestration run found in this project.'}
    data = collect(run)
    # Keep reports and full logs on disk. Only UI fields cross the mod boundary.
    fields = ('title', 'goal', 'run_id', 'progress', 'demo', 'mode', 'all_done',
              'spend_usd', 'run_budget_usd', 'orchestrator', 'approvals', 'decisions')
    result = {key: data.get(key) for key in fields}
    result['run'] = str(run)
    result['workers'] = [{key: worker.get(key) for key in
                          ('id', 'title', 'state', 'model', 'effort', 'objective', 'character', 'last_action')}
                         for worker in data.get('workers', [])]
    result['activity'] = data.get('activity', [])[:12]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', help='Project or run directory')
    args = parser.parse_args()
    try:
        print(json.dumps(snapshot(args.target)))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Cannot read orchestration run: {exc}\n')


if __name__ == '__main__':
    main()
