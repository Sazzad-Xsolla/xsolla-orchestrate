#!/usr/bin/env python3
"""Save or restore a task's write-list files around an attempt.

Usage: snapshot.py <run_dir> <task_id> save|restore [attempt]

save     copies every file in the task's `writes` into workers/<id>/snapshot-a<N>/
         and records which ones did not exist yet.
restore  puts those files back and deletes files the attempt created, so a
         rejected attempt leaves nothing behind. Defaults to the latest snapshot.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path


def expand(root, writes):
    """Concrete files covered by the write list (folders expand to their current files)."""
    out = []
    for w in writes:
        p = Path(w) if Path(w).is_absolute() else root / w
        if w.endswith("/"):
            if p.is_dir():
                out += [f for f in p.rglob("*") if f.is_file()]
            out.append(p)  # remember the folder itself so new files inside it get cleaned
        else:
            out.append(p)
    return out


def key(path):
    # Short and unique: deep absolute paths overflow the filename limit.
    return hashlib.sha1(str(path).encode()).hexdigest()[:12] + "-" + Path(path).name


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    run, task_id, mode = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
    plan = json.loads((run / "plan.json").read_text())
    task = next(t for t in plan["tasks"] if t["id"] == task_id)
    root = Path(plan["project_dir"])
    wdir = run / "workers" / task_id
    attempt = int(sys.argv[4]) if len(sys.argv) > 4 else task.get("attempt", 1)

    if mode == "save":
        snap = wdir / f"snapshot-a{attempt}"
        if snap.exists():
            shutil.rmtree(snap)
        snap.mkdir(parents=True)
        manifest = {"files": {}, "dirs": {}}
        for p in expand(root, task.get("writes", [])):
            if p.is_dir():
                manifest["dirs"][str(p)] = sorted(str(f) for f in p.rglob("*") if f.is_file())
            elif p.exists():
                shutil.copy2(p, snap / key(p))
                manifest["files"][str(p)] = key(p)
            else:
                manifest["files"][str(p)] = None
        (snap / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"saved {len(manifest['files'])} file(s) for {task_id} attempt {attempt}")
        return

    if mode == "restore":
        snaps = sorted(wdir.glob("snapshot-a*"), key=lambda s: int(s.name.split("-a")[1]))
        if len(sys.argv) > 4:
            snaps = [wdir / f"snapshot-a{attempt}"]
        if not snaps or not (snaps[-1] / "manifest.json").exists():
            sys.exit(f"no snapshot for {task_id}")
        snap = snaps[-1]
        manifest = json.loads((snap / "manifest.json").read_text())
        restored = removed = 0
        for path, saved in manifest["files"].items():
            p = Path(path)
            if saved is None:
                if p.exists():
                    p.unlink()
                    removed += 1
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(snap / saved, p)
                restored += 1
        for d, before in manifest["dirs"].items():
            for f in Path(d).rglob("*") if Path(d).is_dir() else []:
                if f.is_file() and str(f) not in before:
                    f.unlink()
                    removed += 1
        print(f"restored {restored} file(s), removed {removed} new file(s) from {snap.name}")
        return

    sys.exit(__doc__)


if __name__ == "__main__":
    main()
