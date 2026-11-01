"""Shared Field Team presentation and decision records. Never executes requests."""
import datetime
import fcntl
import hashlib
import json
from pathlib import Path

from control import atomic_json, orchestrator_only

CREATURES = {
    'pip': {'name': 'Pip', 'role': 'Scout'},
    'rivet': {'name': 'Rivet', 'role': 'Builder'},
    'aegis': {'name': 'Aegis', 'role': 'Guardian'},
}


def read(path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def fingerprint(run, request):
    payload = {'run': str(Path(run).resolve()), 'request': request}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def requests(run, plan=None):
    run = Path(run)
    plan = plan if plan is not None else read(run / 'plan.json', {})
    decisions = read(run / 'decisions.json', {})
    pending, answered = [], []
    ids = set()
    for a in plan.get('approvals', []):
        aid = a.get('id')
        if not isinstance(aid, str) or not aid or aid in ids:
            raise ValueError('Approval requests need unique, non-empty IDs')
        ids.add(aid)
        if a.get('status', 'pending') != 'pending':
            continue
        fp = fingerprint(run, a)
        item = dict(a, fingerprint=fp)
        decision = decisions.get(aid, {})
        if decision.get('fingerprint') == fp:
            answered.append(dict(item, response=decision))
        else:
            pending.append(item)
    return pending, answered


def record_decision(run, aid, choice, expected, source='mission-control'):
    orchestrator_only()
    if choice not in ('approve', 'reject'):
        raise ValueError('Unknown decision')
    if source not in ('mission-control', 'desktop-widget'):
        raise ValueError('Unknown decision source')
    run = Path(run).resolve()
    # All runtime plan writers use this same lock. Lock order is plan, then decisions.
    with (run / 'plan.json.lock').open('a') as plan_lock:
        fcntl.flock(plan_lock, fcntl.LOCK_EX)
        with (run / 'decisions.json.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            pending, _ = requests(run)
            request = next((a for a in pending if a['id'] == aid), None)
            if request is None or request['fingerprint'] != expected:
                raise ValueError('Request changed or was already answered; refresh and review it again')
            decisions = read(run / 'decisions.json', {})
            previous = decisions.get(aid)
            record = {'decision': choice, 'fingerprint': expected, 'source': source,
                      'at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            if previous:
                record['previous'] = previous
            decisions[aid] = record
            atomic_json(run / 'decisions.json', decisions)
    return {'ok': True, 'message': 'Decision recorded; no action was executed'}


def recent_events(path, agent):
    """Bounded log tail; only expose text and tool summaries, never hidden thinking."""
    events = []
    try:
        with Path(path).open('rb') as stream:
            stream.seek(0, 2)
            length = stream.tell()
            stream.seek(max(0, length - 262144))
            if length > 262144:
                stream.readline()
            lines = stream.read().decode('utf-8', 'replace').splitlines()
    except FileNotFoundError:
        return events
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        at = event.get('timestamp') or event.get('at') or ''
        if event.get('type') == 'assistant':
            content = event.get('message', {}).get('content', [])
            for part in content if isinstance(content, list) else []:
                kind = part.get('type')
                text = ''
                if kind == 'text':
                    text = str(part.get('text', '')).strip()
                elif kind == 'tool_use':
                    inp = part.get('input') or {}
                    detail = inp.get('command') or inp.get('file_path') or inp.get('pattern') or ''
                    text = str(part.get('name', 'Tool')) + (': ' + str(detail) if detail else '')
                if text:
                    events.append({'agent': agent, 'at': str(at), 'kind': kind,
                                   'text': text[:4000], 'sequence': index})
        elif event.get('type') == 'result':
            events.append({'agent': agent, 'at': str(at), 'kind': 'result',
                           'text': str(event.get('result') or event.get('subtype') or 'Worker returned')[:4000],
                           'sequence': index})
    return events[-40:]


def enrich(run, data, plan):
    run = Path(run)
    data['run_key'] = hashlib.sha256(str(run.resolve()).encode()).hexdigest()
    data['approvals'], data['decisions'] = requests(run, plan)
    by_task = {t['id']: t for t in plan.get('tasks', [])}
    activity = []
    for worker in data.get('workers', []):
        task = by_task[worker['id']]
        identity = task.get('character') or {}
        if not isinstance(identity, dict):
            identity = {}
        default = 'aegis' if task.get('specialist') == 'review' or task.get('shape') == 'review' else 'pip' if task.get('shape') == 'lookup' else 'rivet'
        creature = identity.get('species', default)
        if creature not in CREATURES:
            creature = default
        worker['character'] = dict(CREATURES[creature], species=creature,
                                   name=identity.get('name') or CREATURES[creature]['name'],
                                   level=identity.get('level'))
        worker['objective'] = task.get('objective') or task.get('title') or 'Goal not recorded'
        worker['done_criteria'] = task.get('done_criteria', [])
        worker['updated_at'] = datetime.datetime.fromtimestamp((run / 'workers' / worker['id'] / 'log.jsonl').stat().st_mtime, datetime.timezone.utc).isoformat() if (run / 'workers' / worker['id'] / 'log.jsonl').exists() else None
        worker['activity'] = recent_events(run / 'workers' / worker['id'] / 'log.jsonl', worker['id'])
        worker['report'] = (run / 'workers' / worker['id'] / 'report.md').read_text(errors='replace')[:16000] if (run / 'workers' / worker['id'] / 'report.md').exists() else ''
        worker['awaiting_approval'] = any(a.get('from_task') == worker['id'] for a in data['approvals'])
        responses = [a['response'] for a in data['decisions'] if a.get('from_task') == worker['id']]
        worker['latest_decision'] = max(responses, key=lambda r: r.get('at', '')) if responses else None
        worker['awaiting_supervisor'] = bool(worker['latest_decision'] and worker['state'] == 'running' and worker['latest_decision'].get('at', '') > (worker['updated_at'] or ''))
        activity.extend(worker['activity'])
    for item in plan.get('log', [])[-40:]:
        activity.append({'agent': 'orchestrator', 'at': str(item.get('at', '')), 'kind': 'coordination', 'text': str(item.get('note', ''))[:4000]})
    for message in data.get('messages', [])[-40:]:
        activity.append({'agent': message.get('sender', 'orchestrator'), 'at': str(message.get('at') or message.get('created_at') or ''), 'kind': 'handoff', 'text': str(message.get('text', ''))[:4000]})
    for decision in data['decisions']:
        response = decision['response']
        activity.append({'agent': decision.get('from_task', 'orchestrator'), 'at': response['at'], 'kind': 'decision', 'text': ('Approved' if response['decision'] == 'approve' else 'Denied') + ': ' + str(decision.get('target', decision['id']))})
    # Timestamps absent from the source remain absent; do not fabricate event times.
    data['activity'] = sorted(activity, key=lambda e: e['at'], reverse=True)[:120]
    configured = plan.get('orchestrator') or {}
    if not isinstance(configured, dict):
        configured = {}
    data['orchestrator'] = {'name': configured.get('name') or 'Claude orchestrator',
                            'model': configured.get('model'), 'effort': configured.get('effort'),
                            'status': configured.get('status') or 'Not recorded',
                            'summary': configured.get('summary') or 'Supervising conversation in Claude Code'}
    return data
