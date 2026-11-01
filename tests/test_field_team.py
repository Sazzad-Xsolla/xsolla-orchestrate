import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import field_team
import field_demo
import status
import serve_dashboard
from control import atomic_json


class FieldTeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = field_demo.create(Path(self.tmp.name) / 'project')

    def tearDown(self):
        self.tmp.cleanup()

    def collect(self):
        with patch.object(status, 'headroom_stats', return_value=None):
            return status.collect(self.run)

    def answer(self, choice='approve', source='mission-control'):
        request = field_team.requests(self.run)[0][0]
        return field_team.record_decision(self.run, request['id'], choice, request['fingerprint'], source)

    def test_claude_routes_goals_and_orchestrator_are_collected(self):
        data = self.collect()
        self.assertEqual(data['orchestrator']['model'], 'opus')
        self.assertEqual(data['workers'][0]['objective'], 'Map catalog endpoints')
        self.assertEqual(data['workers'][1]['model'], 'sonnet')
        self.assertEqual(data['workers'][1]['effort'], 'high')
        self.assertTrue(data['workers'][2]['awaiting_approval'])
        self.assertTrue(data['activity'])

    def test_missing_metadata_is_not_invented(self):
        plan = field_team.read(self.run / 'plan.json', {})
        plan.pop('orchestrator')
        plan['tasks'][0].pop('character')
        atomic_json(self.run / 'plan.json', plan)
        data = self.collect()
        self.assertIsNone(data['orchestrator']['model'])
        self.assertIsNone(data['orchestrator']['effort'])
        self.assertEqual(data['orchestrator']['status'], 'Not recorded')
        self.assertIsNone(data['workers'][0]['character']['level'])

    def test_shared_decision_does_not_mutate_plan_or_execute(self):
        before = (self.run / 'plan.json').read_bytes()
        self.answer(source='desktop-widget')
        self.assertEqual((self.run / 'plan.json').read_bytes(), before)
        data = self.collect()
        self.assertEqual(data['approvals'], [])
        self.assertEqual(data['decisions'][0]['response']['source'], 'desktop-widget')
        self.assertFalse(data['workers'][2]['awaiting_approval'])
        self.assertTrue(data['workers'][2]['awaiting_supervisor'])

    def test_changed_request_and_cross_run_fingerprint_are_rejected(self):
        old = field_team.requests(self.run)[0][0]
        plan = field_team.read(self.run / 'plan.json', {})
        plan['approvals'][0]['target'] = 'Production'
        atomic_json(self.run / 'plan.json', plan)
        with self.assertRaises(ValueError):
            field_team.record_decision(self.run, old['id'], 'approve', old['fingerprint'])
        other = field_demo.create(Path(self.tmp.name) / 'other')
        other_request = field_team.requests(other)[0][0]
        with self.assertRaises(ValueError):
            field_team.record_decision(self.run, old['id'], 'approve', other_request['fingerprint'])

    def test_two_surfaces_cannot_answer_twice(self):
        request = field_team.requests(self.run)[0][0]
        def answer(source):
            try:
                field_team.record_decision(self.run, request['id'], 'approve', request['fingerprint'], source)
                return 'recorded'
            except ValueError:
                return 'stale'
        with concurrent.futures.ThreadPoolExecutor() as pool:
            answers = list(pool.map(answer, ['mission-control', 'desktop-widget']))
        self.assertCountEqual(answers, ['recorded', 'stale'])

    def test_updated_request_reopens_and_preserves_old_decision(self):
        self.answer('reject')
        plan = field_team.read(self.run / 'plan.json', {})
        plan['approvals'][0]['text'] = 'Revised scope'
        atomic_json(self.run / 'plan.json', plan)
        self.assertEqual(len(field_team.requests(self.run)[0]), 1)
        self.answer()
        record = field_team.read(self.run / 'decisions.json', {})['demo-webhook']
        self.assertEqual(record['previous']['decision'], 'reject')

    def test_invalid_decisions_and_worker_writes_are_rejected(self):
        with self.assertRaises(ValueError):
            self.answer('execute')
        with patch.dict('os.environ', {'ORCHESTRATE_WORKER': '1'}):
            with self.assertRaises(ValueError):
                self.answer()

    def test_malformed_decision_store_is_not_overwritten(self):
        (self.run / 'decisions.json').write_text('{broken')
        with self.assertRaises(ValueError):
            field_team.record_decision(self.run, 'demo-webhook', 'approve', 'old')
        self.assertEqual((self.run / 'decisions.json').read_text(), '{broken')

    def test_duplicate_ids_are_not_actionable(self):
        plan = field_team.read(self.run / 'plan.json', {})
        plan['approvals'].append(dict(plan['approvals'][0]))
        atomic_json(self.run / 'plan.json', plan)
        with self.assertRaises(ValueError):
            field_team.requests(self.run)

    def test_log_tail_ignores_partial_lines_and_thinking(self):
        path = self.run / 'workers/scout/log.jsonl'
        path.write_text('x' * 300000 + '\n' + json.dumps({'type': 'assistant', 'message': {'content': [
            {'type': 'thinking', 'thinking': 'hidden reasoning'},
            {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': 'catalog.py'}},
            {'type': 'text', 'text': '<script>literal text</script>'}
        ]}}) + '\n{partial')
        events = field_team.recent_events(path, 'scout')
        self.assertEqual(len(events), 2)
        self.assertIn('Read: catalog.py', events[0]['text'])
        self.assertNotIn('hidden reasoning', json.dumps(events))


class LocalApiTests(unittest.TestCase):
    collect = FieldTeamTests.collect
    def setUp(self):
        FieldTeamTests.setUp(self)
        self.handler = type('IsolatedHandler', (serve_dashboard.Handler,), {'run': self.run, '_cache': (0.0, None), 'token': 'test-session-token'})
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), self.handler)
        self.url = 'http://127.0.0.1:' + str(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.stats = patch.object(status, 'headroom_stats', return_value=None)
        self.stats.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.stats.stop()
        FieldTeamTests.tearDown(self)

    def post(self, body, token='test-session-token', origin=None, path='/decision'):
        request = urllib.request.Request(self.url + path, json.dumps(body).encode(),
            {'Content-Type': 'application/json', 'X-Field-Team-Token': token, 'Origin': origin or self.url})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def test_http_authorization_run_binding_and_shared_state(self):
        data = self.collect()
        a = data['approvals'][0]
        body = {'id': a['id'], 'fingerprint': a['fingerprint'], 'run_key': data['run_key'], 'decision': 'approve'}
        self.assertEqual(self.post(body, token='wrong')[0], 403)
        self.assertEqual(self.post(body, origin='https://example.com')[0], 403)
        self.assertEqual(self.post(dict(body, run_key='other'))[0], 409)
        self.assertEqual(self.post(body)[0], 200)
        self.assertEqual(self.post(body)[0], 409)
        with urllib.request.urlopen(self.url + '/data.json') as response:
            self.assertEqual(json.load(response)['approvals'], [])
        self.assertEqual(self.post(body, path='/stop')[0], 405)

    def test_widget_query_and_host_validation(self):
        with urllib.request.urlopen(self.url + '/?widget=1') as response:
            html = response.read().decode()
            self.assertIn('test-session-token', html)
            self.assertIn('widget-body', html)
        request = urllib.request.Request(self.url, headers={'Host': 'evil.example'})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        self.assertEqual(error.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
