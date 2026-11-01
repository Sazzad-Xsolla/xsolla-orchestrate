"""Local orchestration records. Locks coordinate writers; records are not a sandbox."""
import contextlib
import copy
import fcntl
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", value):
        raise ValueError("IDs must contain 1–64 letters, digits, underscores, or hyphens")
    return value


def orchestrator_only():
    if os.environ.get("ORCHESTRATE_WORKER"):
        raise ValueError("Workers propose changes in their report; the orchestrator updates control records")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return copy.deepcopy(default)


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".record-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def locked_json(path, default=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read_json(path, default)
        yield data
        atomic_json(path, data)


def load_run(run):
    run = Path(run).resolve()
    plan = read_json(run / "plan.json")
    if not isinstance(plan, dict) or not isinstance(plan.get("tasks"), list):
        raise ValueError("Select a run folder containing plan.json and a tasks list")
    ids = [identifier(t["id"]) for t in plan["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Task IDs must be unique")
    project = Path(plan["project_dir"]).resolve()
    return run, plan, project


def task_by_id(plan, task_id):
    identifier(task_id)
    for task in plan["tasks"]:
        if task["id"] == task_id:
            return task
    raise ValueError("Unknown task: " + task_id)
