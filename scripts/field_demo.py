"""Create a persistent, explicitly synthetic Field Team run without model calls."""
import argparse
import datetime
import json
from pathlib import Path

from control import atomic_json


def create(project):
    project = Path(project).resolve()
    run = project / '.xsolla-orchestrator' / 'field-team-demo'
    if (run / 'plan.json').exists():
        return run
    run.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    examples = [
        ('scout', 'Map catalog endpoints', 'lookup', 'sonnet', 'medium', 'pip', 8, 'Checking item pagination'),
        ('build', 'Build sandbox checkout', 'spec', 'sonnet', 'high', 'rivet', 12, 'Running checkout tests'),
        ('review', 'Verify payment events', 'review', 'opus', 'high', 'aegis', 10, 'Waiting to update the sandbox webhook URL'),
    ]
    tasks = []
    for i, (tid, goal, shape, model, effort, species, level, activity) in enumerate(examples):
        task = {'id': tid, 'title': goal, 'objective': goal, 'shape': shape,
                'model': model, 'effort': effort, 'state': 'running', 'runtime': 'headless',
                'specialist': 'review' if tid == 'review' else 'implementation',
                'character': {'species': species, 'level': level},
                'routing_reason': 'Synthetic route for the Field Team demonstration',
                'writes': [], 'depends_on': [], 'done_criteria': ['Provide acceptance evidence'],
                'attempt': 1}
        tasks.append(task)
        worker = run / 'workers' / tid
        worker.mkdir(parents=True, exist_ok=True)
        event = {'type': 'assistant', 'timestamp': (now - datetime.timedelta(seconds=i*8)).isoformat(),
                 'message': {'content': [{'type': 'text', 'text': activity}]}}
        (worker / 'log.jsonl').write_text(json.dumps(event) + '\n')
        (worker / 'report.md').write_text('# Demonstration report\n\nSynthetic activity for visual and interaction testing. No real checkout or webhook changes have been made.\n')
    atomic_json(run / 'plan.json', {
        'run_id': 'field-team-demo', 'title': 'Sandbox storefront · Demonstration',
        'goal': 'Build a sandbox storefront', 'project_dir': str(project), 'demo': True,
        'dashboard_theme': 'xsolla', 'tasks': tasks,
        'orchestrator': {'name': 'Atlas', 'model': 'opus', 'effort': 'high',
                         'status': 'Coordinating', 'summary': 'Waiting for the permission review'},
        'definition_of_done': [{'text': 'Browse catalog items', 'met': False},
                              {'text': 'Complete sandbox checkout', 'met': False},
                              {'text': 'Verify payment events', 'met': False}],
        'approvals': [{'id': 'demo-webhook', 'from_task': 'review', 'kind': 'Update sandbox webhook URL',
                       'target': 'Demo Store · Sandbox · /hooks/v1 → /hooks/v2',
                       'text': 'Replace the sandbox webhook endpoint to verify payment event handling',
                       'status': 'pending'}],
        'log': [{'at': (now - datetime.timedelta(seconds=35)).isoformat(),
                 'note': 'Atlas assigned catalog, checkout, and payment verification goals'}],
    })
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    print(create(parser.parse_args().project))
