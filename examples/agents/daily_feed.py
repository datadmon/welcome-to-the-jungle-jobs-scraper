"""One daily invocation: unseen jobs with bounded rows, pagination and USD cost.

Local seen IDs are authoritative; skip IDs are sent to the Actor before billing.
No schedule is installed. Run serially and keep the state file between days.
"""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path

from common import atomic_json, bounded_items
from config import ACTOR, MAX_FIELD, SKIP_FIELD


def cost_cap(value):
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Cost must be a finite positive USD amount') from None
    if not amount.is_finite() or amount < Decimal('0.01') or amount > Decimal('1'):
        raise ValueError('Cost cap must be $0.01..$1 per invocation')
    return float(amount)


def feed(client, *, state_path, out_path, search, max_rows=50, max_cost='0.05', page_size=25, max_pages=2):
    cap = cost_cap(max_cost)
    if not 1 <= page_size <= 1000 or not 1 <= max_pages <= 100 or not 1 <= max_rows <= page_size * max_pages:
        raise ValueError('Row cap must fit within the bounded page budget')
    if Path(state_path).resolve() == Path(out_path).resolve():
        raise ValueError('State and output paths must differ')
    forbidden = {MAX_FIELD, SKIP_FIELD, 'onlyNewSinceLastRun', 'stateName'}
    if forbidden.intersection(search):
        raise ValueError('Search input cannot override delivery or row-cap fields')
    # Three-day overlap handles late postings. Only unseen IDs reach the output.
    search = {'postedWithinDays': 3, **search}
    fingerprint = hashlib.sha256(json.dumps([ACTOR, search], sort_keys=True).encode()).hexdigest()
    path = Path(state_path)
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'fingerprint': fingerprint, 'seen': []}
    if state['fingerprint'] != fingerprint:
        raise ValueError('Search changed; use a different state file to start a new feed')
    seen = set(map(str, state['seen']))
    if len(seen) > 10000:
        raise ValueError('This small-client example supports 10,000 IDs; archive the feed before continuing')
    if state.get('pending_run'):
        run = client.run(state['pending_run']).wait_for_finish(wait_secs=180)
    else:
        run_input = {**search, MAX_FIELD: max_rows, SKIP_FIELD: sorted(seen), 'onlyNewSinceLastRun': False}
        run = client.actor(ACTOR).start(run_input=run_input, max_total_charge_usd=cap, timeout_secs=180, memory_mbytes=512)
        state['pending_run'] = run['id']
        atomic_json(path, state)
        run = client.run(run['id']).wait_for_finish(wait_secs=180)
    if not run or run.get('status') != 'SUCCEEDED':
        raise RuntimeError('Run did not succeed; saved pending_run allows inspection/resume without starting another run')
    rows = bounded_items(client.dataset(run['defaultDatasetId']), page_size=page_size, max_pages=max_pages)
    if any(row.get('id') is None for row in rows):
        raise ValueError('Missing stable job ID; refusing to advance delivery state')
    fresh = []
    for row in rows:
        key = str(row['id'])
        if key not in seen:
            fresh.append(row)
            seen.add(key)
    if len(seen) > 10000:
        raise ValueError('Feed reached the 10,000-ID example limit; output/state not advanced')
    # Save output first. Failed pagination or output writes never advance seen IDs.
    atomic_json(out_path, {'runId': run['id'], 'datasetId': run['defaultDatasetId'], 'jobs': fresh})
    atomic_json(path, {'fingerprint': fingerprint, 'seen': sorted(seen), 'last_run': run['id']})
    return fresh, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).with_name('daily-input.json'))
    parser.add_argument('--state', type=Path, default=Path('feed-state.json'))
    parser.add_argument('--out', type=Path, default=Path('feed-output.json'))
    parser.add_argument('--max-rows', type=int, default=50)
    parser.add_argument('--max-cost', default='0.05')
    parser.add_argument('--page-size', type=int, default=25)
    parser.add_argument('--max-pages', type=int, default=2)
    args = parser.parse_args()
    from apify_client import ApifyClient
    rows, run = feed(ApifyClient(os.environ['APIFY_TOKEN']), state_path=args.state, out_path=args.out,
                     search=json.loads(args.input.read_text(encoding='utf-8')), max_rows=args.max_rows,
                     max_cost=args.max_cost, page_size=args.page_size, max_pages=args.max_pages)
    print(f"{len(rows)} unseen jobs; run {run['id']}; output {args.out}")


if __name__ == '__main__':
    main()
