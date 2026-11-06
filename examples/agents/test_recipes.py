import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from common import bounded_items
from config import ACTOR, MAX_FIELD, SKIP_FIELD
from daily_feed import feed
from job_documents import JobDocumentLoader


class RecipesTest(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads((Path(__file__).parents[1] / 'sample-output.json').read_text(encoding='utf-8'))
        self.client = MagicMock()
        self.client.actor.return_value.start.return_value = {'id': 'run-1'}
        self.client.run.return_value.wait_for_finish.return_value = {'id': 'run-1', 'status': 'SUCCEEDED', 'defaultDatasetId': 'data-1'}
        ds = self.client.dataset.return_value
        ds.get.return_value = {'itemCount': len(self.rows)}
        ds.list_items.side_effect = lambda **kw: type('Page', (), {'total': len(self.rows), 'items': self.rows[kw['offset']:kw['offset'] + kw['limit']]})()

    def test_real_framework_documents_have_original_citations(self):
        docs = JobDocumentLoader(self.rows + self.rows[:1]).load()
        self.assertEqual(len(docs), len({r['id'] for r in self.rows}))
        self.assertEqual(docs[0].metadata['source'], self.rows[0]['url'])
        self.assertIn(self.rows[0]['url'], docs[0].page_content)
        self.assertEqual(docs[0].metadata['posted_at'], self.rows[0]['postedAt'])
        self.assertEqual(docs[0].metadata['actor'], ACTOR)

    def test_missing_source_is_rejected(self):
        with self.assertRaises(ValueError):
            JobDocumentLoader([{'id': 'x'}]).load()

    def test_daily_delta_and_apify_cost_limit(self):
        with TemporaryDirectory() as d:
            kw = dict(state_path=Path(d)/'state.json', out_path=Path(d)/'out.json', search={}, max_rows=6, page_size=2, max_pages=3)
            rows, _ = feed(self.client, **kw)
            self.assertEqual(len(rows), len(self.rows))
            rows, _ = feed(self.client, **kw)
            self.assertEqual(rows, [])
            start = self.client.actor.return_value.start.call_args.kwargs
            self.assertEqual(start['max_total_charge_usd'], 0.05)
            self.assertEqual(start['run_input'][MAX_FIELD], 6)
            self.assertEqual(set(start['run_input'][SKIP_FIELD]), {str(r['id']) for r in self.rows})
            self.assertEqual(start['run_input']['postedWithinDays'], 3)

    def test_page_budget_failure_preserves_seen_and_resumes_same_run(self):
        with TemporaryDirectory() as d:
            state, out = Path(d)/'state.json', Path(d)/'out.json'
            with self.assertRaises(ValueError):
                feed(self.client, state_path=state, out_path=out, search={}, max_rows=2, page_size=2, max_pages=1)
            self.assertFalse(out.exists())
            self.assertEqual(json.loads(state.read_text())['seen'], [])
            feed(self.client, state_path=state, out_path=out, search={}, max_rows=6, page_size=2, max_pages=3)
            self.assertEqual(self.client.actor.return_value.start.call_count, 1)

    def test_output_failure_keeps_pending_run(self):
        with TemporaryDirectory() as d:
            state, out = Path(d)/'state.json', Path(d)/'out.json'
            import daily_feed
            real_write = daily_feed.atomic_json
            def write(path, value):
                if Path(path) == out:
                    raise OSError('disk full')
                real_write(path, value)
            with patch('daily_feed.atomic_json', side_effect=write), self.assertRaises(OSError):
                feed(self.client, state_path=state, out_path=out, search={})
            saved = json.loads(state.read_text())
            self.assertEqual(saved['seen'], [])
            self.assertEqual(saved['pending_run'], 'run-1')

    def test_invalid_budgets_never_start_a_run(self):
        with TemporaryDirectory() as d:
            for cost in ['nan', 'inf', '-1', '0', '2']:
                with self.assertRaises(ValueError):
                    feed(self.client, state_path=Path(d)/'s', out_path=Path(d)/'o', search={}, max_cost=cost)
            self.client.actor.assert_not_called()

    def test_changed_search_cannot_reuse_state(self):
        with TemporaryDirectory() as d:
            kw = dict(state_path=Path(d)/'s', out_path=Path(d)/'o')
            feed(self.client, search={}, **kw)
            with self.assertRaises(ValueError):
                feed(self.client, search={'postedWithinDays': 7}, **kw)

    def test_short_page_does_not_silently_skip_rows(self):
        self.client.dataset.return_value.list_items.side_effect = lambda **kw: type('Page', (), {'total': len(self.rows), 'items': []})()
        with self.assertRaises(ValueError):
            bounded_items(self.client.dataset.return_value)

    def test_lagging_metadata_does_not_drop_live_rows(self):
        self.client.dataset.return_value.get.return_value = {'itemCount': 0}
        self.assertEqual(bounded_items(self.client.dataset.return_value), self.rows)


if __name__ == '__main__':
    unittest.main()
