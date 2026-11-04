import json
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
import start_views


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="startup project ")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve()
        self.run = self.project / ".xsolla-orchestrator/exact-run"
        self.run.mkdir(parents=True)
        self.plan = {"project_dir": str(self.project), "goal": "Fix the checkout",
                     "definition_of_done": [{"text": "Checkout works", "met": False}],
                     "tasks": [{"id": "impl", "model": "sonnet", "effort": "medium",
                                "budget_usd": 1, "writes": ["src/"], "accept": "npm test"}]}
        self.save()

    def save(self):
        control.atomic_json(self.run / "plan.json", self.plan)

    def test_unconfirmed_dispatch_and_critic_do_not_launch(self):
        with self.assertRaisesRegex(ValueError, "unconfirmed"):
            dispatch.claim(self.run, "impl")
        fake = self.project / "bin"
        fake.mkdir()
        marker = self.project / "agent-started"
        cli = fake / "claude"
        cli.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\n')
        cli.chmod(0o755)
        result = subprocess.run(["bash", str(ROOT / "scripts/critique_brief.sh"), str(self.run), "impl"],
                                env=dict(os.environ, PATH=str(fake) + os.pathsep + os.environ["PATH"]),
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unconfirmed", result.stderr)
        self.assertFalse(marker.exists())
        self.assertNotIn("state", control.read_json(self.run / "plan.json")["tasks"][0])

    def test_confirmation_survives_progress_but_not_scope_or_budget_changes(self):
        dispatch_approval.approve(self.run, "Yes, run this dispatch plan")
        plan = control.read_json(self.run / "plan.json")
        plan["tasks"][0]["state"] = "running"
        plan["definition_of_done"][0].update(met=True, evidence="passed")
        dispatch_approval.require_approval(self.run, plan)
        for field, value in (("budget_usd", 2), ("model", "opus"), ("writes", ["other/"]),
                             ("accept", "npm run different-test")):
            revised = json.loads(json.dumps(plan))
            revised["tasks"][0][field] = value
            with self.assertRaisesRegex(ValueError, "changed"):
                dispatch_approval.require_approval(self.run, revised)
        with self.assertRaisesRegex(ValueError, "changed"):
            dispatch_approval.require_approval(self.project / "different-run", plan)

    def test_open_views_pins_both_paths_and_retargets_existing_app(self):
        app = self.project / "Field Team.app"
        binary = app / "Contents/MacOS/FieldTeam"
        binary.parent.mkdir(parents=True)
        binary.touch()
        url = "http://127.0.0.1:41234/"
        with patch.object(start_views, "ensure_dashboard", return_value=url) as server, \
                patch.object(start_views.subprocess, "run") as launch, \
                patch.object(start_views.sys, "platform", "darwin"):
            for _ in range(2):
                result = start_views.open_views(self.run, app)
                self.assertEqual(result["run"], str(self.run))
            server.assert_called_with(ROOT, self.run)
            commands = [call.args[0] for call in launch.call_args_list]
        target_path = self.run / "field-team-target.json"
        self.assertEqual(commands, [["/usr/bin/open", "-a", str(app), str(target_path)],
                                    ["/usr/bin/open", url]] * 2)
        target = control.read_json(target_path)
        self.assertEqual(target["run"], str(self.run))
        self.assertEqual(target["skill"], str(ROOT))
        self.assertNotIn("dispatch_confirmation", control.read_json(self.run / "plan.json"))


if __name__ == "__main__":
    unittest.main()
