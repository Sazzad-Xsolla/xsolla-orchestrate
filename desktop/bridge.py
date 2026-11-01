"""Desktop adapter for xsolla-orchestrate's shared collector and local view."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse
import urllib.request


def healthy(url, run):
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.username or parsed.password:
            return False
        with urllib.request.urlopen(url.rstrip('/') + '/health', timeout=1) as response:
            data = json.load(response)
        return data.get('service') == 'xsolla-field-team' and data.get('run') == str(run)
    except (OSError, ValueError):
        return False


def ensure_dashboard(skill, run):
    with (run / '.field-team-server.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = run / 'dashboard.url'
        url = record.read_text().strip() if record.exists() else ''
        if healthy(url, run):
            return url
        with (run / 'dashboard-server.log').open('a') as output:
            process = subprocess.Popen([sys.executable, str(skill / 'scripts/serve_dashboard.py'), str(run)],
                                       stdout=output, stderr=output, stdin=subprocess.DEVNULL,
                                       start_new_session=True)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            url = record.read_text().strip() if record.exists() else ''
            if healthy(url, run):
                return url
            if process.poll() is not None:
                break
            time.sleep(.1)
        raise ValueError('Cannot start Mission Control; inspect dashboard-server.log in the run folder')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill', required=True)
    parser.add_argument('--run')
    parser.add_argument('--demo-project')
    args = parser.parse_args()
    skill = Path(args.skill).expanduser().resolve()
    if not (skill / 'scripts/field_team.py').is_file():
        raise ValueError('Choose the updated xsolla-orchestrate folder with Field Team support')
    sys.path.insert(0, str(skill / 'scripts'))
    from serve_dashboard import resolve_run
    from field_demo import create
    import status
    run = create(args.demo_project) if args.demo_project else resolve_run(args.run or '')
    data = status.collect(run)
    data['run'] = str(run)
    data['dashboard'] = ensure_dashboard(skill, run)
    data['complete'] = data.get('all_done', False)
    print(json.dumps(data))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc)}))
        sys.exit(1)
