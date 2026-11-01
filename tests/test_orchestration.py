import concurrent.futures
import importlib.util
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
import coordinate
import dispatch
import memory
import route
import status
import watchdog
import install


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="xsolla test ")
        self.project = Path(self.tmp.name)
        self.run = self.project / ".xsolla-orchestrator/run-one"
        self.run.mkdir(parents=True)
        self.tasks = []
        for task_id in ("impl", "review", "other"):
            task = {"id": task_id, "title": task_id, "shape": "spec", "state": "planned",
                    "model": "sonnet", "effort": "medium", "budget_usd": 1, "routing_reason": "Agreed specification",
                    "runtime": "headless", "writes": [], "depends_on": [], "attempt": 1,
                    "done_criteria": ["Evidence exists"], "accept": "test -f evidence.txt", "specialist": "implementation"}
            self.tasks.append(task)
            worker = self.run / "workers" / task_id
            worker.mkdir(parents=True)
            (worker / "brief.md").write_text("# Task\nCheck the evidence file and report its content.\n")
        self.plan = {"run_id": "run-one", "project_dir": str(self.project), "tasks": self.tasks,
                     "title": "Test run", "goal": "Verify coordination", "definition_of_done": [], "approvals": []}
        self.save()
        (self.project / "evidence.txt").write_text("Confirmed project convention\n")
        for task in self.tasks:
            self.critique(task)

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        control.atomic_json(self.run / "plan.json", self.plan)

    def critique(self, task):
        control.atomic_json(self.run / "workers" / task["id"] / "critique-audit.json",
                            {"verdict": "clear", "fingerprint": dispatch.critique_fingerprint(self.run, task)})

    def test_risk_changes_route_without_changing_specialist(self):
        task = {"shape": "mechanical", "risk": "high", "specialist": "review"}
        selected = route.recommend(task)
        self.assertEqual(selected["shape"], "tricky")
        self.assertEqual(selected["effort"], "high")
        self.assertEqual(task["specialist"], "review")
        with self.assertRaises(ValueError):
            route.recommend({"shape": "invented"})

    def test_changed_brief_or_task_invalidates_critic(self):
        dispatch.validate(self.run, self.plan, self.project, "impl")
        (self.run / "workers/impl/brief.md").write_text("Changed assignment")
        with self.assertRaisesRegex(ValueError, "critique"):
            dispatch.validate(self.run, self.plan, self.project, "impl")
        self.critique(self.tasks[0])
        self.tasks[0]["accept"] = "test -f another-file"
        with self.assertRaisesRegex(ValueError, "critique"):
            dispatch.validate(self.run, self.plan, self.project, "impl")

    def test_dependencies_and_directory_overlap_block_dispatch(self):
        self.tasks[1]["depends_on"] = ["impl"]
        self.critique(self.tasks[1])
        with self.assertRaisesRegex(ValueError, "Dependency"):
            dispatch.validate(self.run, self.plan, self.project, "review")
        self.tasks[0].update(state="running", writes=["src/"])
        self.tasks[2]["writes"] = ["src/module.py"]
        self.critique(self.tasks[2])
        with self.assertRaisesRegex(ValueError, "overlaps"):
            dispatch.validate(self.run, self.plan, self.project, "other")

    def test_concurrent_claims_do_not_duplicate_worker(self):
        def attempt():
            try:
                dispatch.claim(self.run, "impl")
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(sum(results), 1)

    def test_messages_deliver_only_to_recipient_and_keep_reply_trace(self):
        first = coordinate.send(self.run, "impl", "review", "question", "Which timestamp format?", "events.md:1")
        self.assertEqual(coordinate.context(self.run, "other")["messages"], [])
        self.assertEqual(coordinate.messages(self.run)[0]["delivery"], "queued")
        snapshot = coordinate.context(self.run, "review", mark=True)
        self.assertEqual(snapshot["messages"][0]["id"], first["id"])
        self.assertEqual(coordinate.messages(self.run)[0]["delivery"], "included in dispatch")
        coordinate.send(self.run, "review", "impl", "answer", "Use UTC offsets", reply_to=first["id"])
        with self.assertRaises(ValueError):
            coordinate.send(self.run, "other", "impl", "answer", "Wrong thread", reply_to=first["id"])
        # Resumed contexts retain previous handoffs, not only newly queued messages.
        self.assertEqual(len(coordinate.context(self.run, "review")["messages"]), 1)

    def test_message_limit_and_parallel_writers(self):
        def send(index):
            return coordinate.send(self.run, "impl", "review", "finding", str(index))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(send, range(8)))
        self.assertEqual(len(coordinate.messages(self.run)), 8)
        with self.assertRaisesRegex(ValueError, "limit"):
            send(9)

    def test_memory_requires_verified_current_evidence_and_review(self):
        lesson = memory.propose(self.run, "impl", "implementation", "Use UTC offsets", "evidence.txt")
        self.assertEqual(memory.context(self.project, "implementation")["lessons"], [])
        with self.assertRaisesRegex(ValueError, "verified"):
            memory.review(self.project, lesson["id"], "Reviewer", "Checked")
        self.tasks[0].update(state="verified", accept_results=[{"passed": True, "exit": 0, "attempt": 1}])
        self.save()
        memory.review(self.project, lesson["id"], "Reviewer", "Checked source and acceptance")
        self.assertEqual(len(memory.context(self.project, "implementation")["lessons"]), 1)
        memory.review(self.project, lesson["id"], "Reviewer", "Superseded", retire=True)
        self.assertEqual(memory.context(self.project, "implementation")["lessons"], [])

    def test_memory_rejects_changed_evidence_and_cross_project_leak(self):
        lesson = memory.propose(self.run, "impl", "implementation", "Convention", "evidence.txt")
        self.tasks[0].update(state="verified", accept_results=[{"passed": True, "exit": 0, "attempt": 1}])
        self.save()
        (self.project / "evidence.txt").write_text("Changed contract")
        with self.assertRaisesRegex(ValueError, "changed"):
            memory.review(self.project, lesson["id"], "Reviewer", "Checked")
        with tempfile.TemporaryDirectory() as other:
            self.assertEqual(memory.context(Path(other), "implementation")["lessons"], [])

    def test_approved_memory_with_changed_evidence_is_not_injected(self):
        lesson = memory.propose(self.run, 'impl', 'implementation', 'Convention', 'evidence.txt')
        self.tasks[0].update(state='verified', accept_results=[{'passed': True, 'exit': 0, 'attempt': 1}])
        self.save()
        memory.review(self.project, lesson['id'], 'Reviewer', 'Checked evidence')
        (self.project / 'evidence.txt').write_text('Superseded convention')
        self.assertEqual(memory.context(self.project, 'implementation')['lessons'], [])
        self.assertEqual(memory.snapshot(self.project)[0]['status'], 'stale')

    def test_worker_mutation_and_control_paths_are_rejected(self):
        with patch.dict(os.environ, {"ORCHESTRATE_WORKER": "impl"}):
            with self.assertRaises(ValueError):
                coordinate.send(self.run, "impl", "review", "finding", "Bypass")
        for path in ("../escape", ".xsolla-orchestrator/plan.json", ".", "/tmp/outside"):
            with self.assertRaises(ValueError):
                dispatch.write_paths({"writes": [path]}, self.project)

    def test_watchdog_detects_loop_but_allows_successful_edit_cycles(self):
        log = self.run / "loop.jsonl"
        events = []
        for i in range(5):
            events.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": str(i), "name": "Read", "input": {"file_path": "same.py"}}]}})
        log.write_text("\n".join(json.dumps(e) for e in events))
        self.assertFalse(watchdog.analyze(log, [], "unused")["healthy"])
        events = []
        for i in range(6):
            events.extend([{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": str(i), "name": "Edit", "input": {"file_path": "source.py"}}]}},
                           {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": str(i), "content": "ok", "is_error": False}]}}])
        log.write_text("\n".join(json.dumps(e) for e in events))
        self.assertTrue(watchdog.analyze(log, ["source.py"], "unused")["healthy"])

    def test_installer_refuses_to_overwrite_existing_skill(self):
        destination = self.project / "skills/xsolla-orchestrate"
        self.assertEqual(install.install(destination).resolve(), ROOT)
        with self.assertRaises(ValueError):
            install.install(destination)

    def test_dispatch_with_fake_runtime_receives_context_without_model_calls(self):
        coordinate.send(self.run, "review", "impl", "finding", "Use the agreed UTC contract", "evidence.txt")
        fake = self.project / "bin"
        fake.mkdir()
        claude = fake / "claude"
        claude.write_text('#!/usr/bin/env python3\nimport json,sys\nprompt=sys.argv[sys.argv.index("-p")+1]\nassert "Use the agreed UTC contract" in prompt\nassert "Implementation specialist" in prompt\nprint(json.dumps({"type":"result","subtype":"success","total_cost_usd":0,"result":"fixture worker finished"}))\n')
        claude.chmod(0o755)
        with patch.dict(os.environ, {"PATH": str(fake) + os.pathsep + os.environ["PATH"], "ORCH_ALLOW_UNWRAPPED": "1"}):
            code = dispatch.dispatch(self.run, "impl")
        self.assertEqual(code, 0)
        plan = control.read_json(self.run / "plan.json")
        self.assertEqual(plan["tasks"][0]["state"], "awaiting review")
        self.assertEqual(coordinate.messages(self.run)[0]["delivery"], "included in dispatch")

    def test_snapshot_escapes_embedded_script_terminators(self):
        with patch.object(status, "headroom_stats", return_value=None):
            data = status.collect(self.run)
        data["goal"] = '</script><script>window.injected=true</script>'
        html = status.render_html(data)
        self.assertNotIn('</script><script>window.injected', html)
        self.assertIn('Xsolla Field Team', html)

    def test_four_worker_reservations_block_fifth_task(self):
        for index in range(4):
            self.plan['tasks'].append({'id': 'active' + str(index), 'state': 'dispatching', 'writes': []})
        with self.assertRaisesRegex(ValueError, 'Four workers'):
            dispatch.validate(self.run, self.plan, self.project, 'impl')

    def test_old_attempt_acceptance_cannot_approve_new_memory(self):
        lesson = memory.propose(self.run, 'impl', 'implementation', 'Convention', 'evidence.txt')
        self.tasks[0].update(state='verified', attempt=2,
                             accept_results=[{'passed': True, 'exit': 0, 'attempt': 1}])
        self.save()
        with self.assertRaisesRegex(ValueError, 'verified'):
            memory.review(self.project, lesson['id'], 'Reviewer', 'Checked')

    def test_acceptance_records_real_command_result(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/accept.py'), str(self.run), 'impl'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        task = control.read_json(self.run / 'plan.json')['tasks'][0]
        self.assertTrue(task['accept_results'][-1]['passed'])
        self.assertEqual(task['state'], 'planned')  # Passing a command is not final review.

    def test_critic_script_binds_verdict_to_current_task(self):
        fake = self.project / 'critic-bin'
        fake.mkdir()
        executable = fake / 'claude'
        executable.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"result":"VERDICT: clear","total_cost_usd":0}))\n')
        executable.chmod(0o755)
        env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'])
        result = subprocess.run(['bash', str(ROOT / 'scripts/critique_brief.sh'), str(self.run), 'impl'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        audit = control.read_json(self.run / 'workers/impl/critique-audit.json')
        self.assertEqual(audit['fingerprint'], dispatch.critique_fingerprint(self.run, self.tasks[0]))

    def test_init_and_list_use_isolated_namespace_with_spaces(self):
        result = subprocess.run(['bash', str(ROOT / 'scripts/init_run.sh'), str(self.project), 'smoke'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        created = Path(result.stdout.strip())
        self.assertEqual(created.parent.name, '.xsolla-orchestrator')
        self.assertFalse((self.project / '.orchestrator').exists())
        listed = subprocess.run(['bash', str(ROOT / 'scripts/list_runs.sh'), str(self.project)], capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn(str(created), listed.stdout)


if __name__ == "__main__":
    unittest.main()
