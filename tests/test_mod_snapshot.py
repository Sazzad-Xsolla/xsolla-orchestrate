import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from mod_snapshot import resolve_run, snapshot


class ModSnapshotTests(unittest.TestCase):
    def test_empty_project_and_explicit_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.assertIsNone(snapshot(project)['run'])
            run = project / '.xsolla-orchestrator' / 'example'
            run.mkdir(parents=True)
            (run / 'plan.json').write_text('{}')
            self.assertEqual(resolve_run(run), run.resolve())

    def test_newest_run_matches_project_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / '.xsolla-orchestrator'
            for name, stamp in [('older', 1), ('newer', 2)]:
                run = runs / name
                run.mkdir(parents=True)
                (run / 'plan.json').write_text('{}')
                os.utime(run, (stamp, stamp))
            self.assertEqual(resolve_run(tmp), (runs / 'newer').resolve())

    def test_uses_runtime_review_state_and_omits_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'plan.json').write_text(json.dumps({'tasks': []}))
            state = {'workers': [{'id': 't1', 'state': 'awaiting review', 'report': 'private report'}],
                     'activity': [{'text': str(i)} for i in range(20)], 'approvals': []}
            with patch('mod_snapshot.collect', return_value=state):
                result = snapshot(run)
            self.assertEqual(result['workers'][0]['state'], 'awaiting review')
            self.assertNotIn('report', result['workers'][0])
            self.assertEqual(len(result['activity']), 12)


if __name__ == '__main__':
    unittest.main()
