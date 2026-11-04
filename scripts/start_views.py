#!/usr/bin/env python3
"""Open the desktop widget and localhost dashboard for one exact run; never launch agents."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from control import atomic_json, load_run

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "desktop"))
from bridge import ensure_dashboard


def open_views(run_path, app_path=None):
    run, _, project = load_run(run_path)
    if sys.platform != "darwin":
        raise ValueError("The Field Team desktop widget requires macOS")
    app = Path(app_path).expanduser().resolve() if app_path else SKILL / "desktop/dist/Xsolla Field Team.app"
    binary = app / "Contents/MacOS/FieldTeam"
    sources = list((SKILL / "desktop").glob("*.swift")) + [SKILL / "desktop/bridge.py", SKILL / "desktop/build.sh"]
    if not binary.is_file() or any(path.stat().st_mtime > binary.stat().st_mtime for path in sources):
        subprocess.run(["bash", str(SKILL / "desktop/build.sh"), str(app.parent)], check=True)
    url = ensure_dashboard(SKILL, run)
    # A document-open event retargets an already-running app as well as a fresh launch.
    # Never depend on defaults, cwd, demo mode, or newest-run discovery.
    target = run / "field-team-target.json"
    atomic_json(target, {"field_team_target": 1, "run": str(run), "skill": str(SKILL)})
    subprocess.run(["/usr/bin/open", "-a", str(app), str(target)], check=True)
    subprocess.run(["/usr/bin/open", url], check=True)
    result = {"project": str(project), "run": str(run), "dashboard": url, "widget": str(app)}
    atomic_json(run / "views.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("--app", help="Optional absolute path to the desktop app bundle")
    args = parser.parse_args()
    print(json.dumps(open_views(args.run, args.app), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
