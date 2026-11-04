import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import control
import dispatch
import dispatch_approval
import dispatch_wave


class DispatchWaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="parallel workers ")
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.run = self.project / ".xsolla-orchestrator/run"
        self.tasks = []
        for task_id in ("alpha", "beta"):
            worker = self.run / "workers" / task_id
            worker.mkdir(parents=True)
            (worker / "brief.md").write_text("Inspect the assigned file and report.\n")
            self.tasks.append({
                "id": task_id, "title": task_id, "state": "planned", "attempt": 1,
                "runtime": "headless", "model": "sonnet", "effort": "medium",
                "budget_usd": 1, "routing_reason": "Agreed task", "writes": [task_id + ".txt"],
                "depends_on": [], "done_criteria": ["Report exists"], "accept": "true",
            })
        self.plan = {"run_id": "run", "project_dir": str(self.project), "goal": "Two independent tasks",
                     "tasks": self.tasks, "definition_of_done": [], "approvals": []}
        self.save_reviewed()

    def save_reviewed(self):
        self.plan["dispatch_confirmation"] = {
            "source": "chat", "confirmation": "Approve this fixture plan",
            "fingerprint": dispatch_approval.fingerprint(self.run, self.plan),
        }
        control.atomic_json(self.run / "plan.json", self.plan)
        for task in self.tasks:
            control.atomic_json(self.run / "workers" / task["id"] / "critique-audit.json", {
                "verdict": "clear", "fingerprint": dispatch.critique_fingerprint(self.run, task),
            })

    def test_preflight_leaves_plan_unchanged(self):
        before = (self.run / "plan.json").read_bytes()
        dispatch_wave.check_wave(self.run, ["alpha", "beta"])
        self.assertEqual(before, (self.run / "plan.json").read_bytes())

    def test_invalid_groups_launch_nothing(self):
        cases = ("overlap", "dependency", "capacity", "duplicate", "approval", "critique")
        baseline = copy.deepcopy(self.plan)
        for case in cases:
            with self.subTest(case=case):
                self.plan = copy.deepcopy(baseline)
                self.tasks = self.plan["tasks"]
                ids = ["alpha", "beta"]
                if case == "overlap":
                    self.tasks[1]["writes"] = ["alpha.txt"]
                elif case == "dependency":
                    self.tasks[1]["depends_on"] = ["alpha"]
                elif case == "capacity":
                    self.plan["tasks"].extend({"id": f"active-{i}", "state": "running", "writes": []} for i in range(3))
                elif case == "duplicate":
                    ids = ["alpha", "alpha"]
                # Only the two original tasks have briefs to review.
                self.tasks = self.plan["tasks"][:2]
                self.save_reviewed()
                if case == "approval":
                    self.plan.pop("dispatch_confirmation")
                    control.atomic_json(self.run / "plan.json", self.plan)
                elif case == "critique":
                    (self.run / "workers/beta/critique-audit.json").unlink()
                before = (self.run / "plan.json").read_bytes()
                with patch.object(dispatch_wave.subprocess, "Popen") as launch:
                    with self.assertRaises(ValueError):
                        dispatch_wave.dispatch_wave(self.run, ids)
                    launch.assert_not_called()
                self.assertEqual(before, (self.run / "plan.json").read_bytes())

    def test_workers_overlap_through_real_dispatchers(self):
        fake = self.project / "bin"
        fake.mkdir()
        executable = fake / "claude"
        executable.write_text('''#!/usr/bin/env python3
import json, os, time
from pathlib import Path
task = os.environ["ORCHESTRATE_WORKER"]
Path(task + ".started").write_text("started")
deadline = time.monotonic() + 15
while not all(Path(name + ".started").exists() for name in ("alpha", "beta")):
    if time.monotonic() > deadline:
        raise SystemExit("peer did not start while I was running")
    time.sleep(0.02)
Path(task + ".overlapped").write_text("both started before completion")
print(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0, "result": "parallel fixture finished"}))
''')
        executable.chmod(0o755)
        with patch.dict(os.environ, {"PATH": str(fake) + os.pathsep + os.environ["PATH"], "ORCH_ALLOW_UNWRAPPED": "1"}):
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/dispatch_wave.py"), str(self.run), "alpha", "beta"],
                capture_output=True, text=True, timeout=45,
            )
        logs = "\n".join((self.run / "workers" / task / "dispatch.log").read_text() for task in ("alpha", "beta"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + logs)
        plan = control.read_json(self.run / "plan.json")
        for task in plan["tasks"]:
            self.assertEqual(task["state"], "awaiting review")
            self.assertTrue((self.project / (task["id"] + ".overlapped")).exists())

    def test_launch_failure_reaps_already_started_dispatcher(self):
        with patch.object(dispatch_wave.subprocess, "Popen") as launch:
            first = launch.return_value
            first.wait.return_value = 0
            launch.side_effect = [first, OSError("fixture launch failure")]
            with self.assertRaisesRegex(OSError, "fixture launch failure"):
                dispatch_wave.dispatch_wave(self.run, ["alpha", "beta"])
            first.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
