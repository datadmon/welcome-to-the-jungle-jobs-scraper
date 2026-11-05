"""Welcome to the Jungle scraper: run the hosted Apify Actor `data_daemon/welcome-to-the-jungle-jobs-scraper` and save the jobs as JSON and CSV.

    pip install apify-client
    export APIFY_TOKEN=...            # Apify Console > Settings > Integrations (free account works)
    python scrape.py --keyword "data engineer" --max 50
    python scrape.py --input input.json             # any field of the Actor's input schema
    python scrape.py --keyword "data engineer" --only-new my-feed   # daily: only jobs not delivered before

Unofficial; not affiliated with Welcome to the Jungle. Price: $0.80 per 1,000 jobs, full description included, plus $0.001 per run.
"""
import argparse
import csv
import json
import os
import sys

from apify_client import ApifyClient

ACTOR = "data_daemon/welcome-to-the-jungle-jobs-scraper"
CSV_COLUMNS = ["id", "postedAt", "title", "company", "locations", "countryCodes", "contractType", "remoteMode", "salary", "experienceLevel", "url"]


def flat(value):
    if isinstance(value, dict):
        return value.get("name") or value.get("title") or json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "; ".join(flat(v) for v in value)
    return "" if value is None else value


def main():
    ap = argparse.ArgumentParser(description="Scrape Welcome to the Jungle jobs to JSON and CSV")
    ap.add_argument("--keyword", action="append", help="search keyword (repeatable)")
    ap.add_argument("--city", action="append", help="city / location filter (repeatable)")
    ap.add_argument("--days", type=int, help="only jobs posted within N days")
    ap.add_argument("--max", type=int, default=50, help="max jobs in total (0 = no limit)")
    ap.add_argument("--only-new", metavar="FEED", help="return only jobs not delivered to this feed name before")
    ap.add_argument("--input", help="JSON file with the full Actor input (overrides the flags above)")
    ap.add_argument("--out", default="welcome-jobs", help="output file prefix")
    ap.add_argument("--max-cost", type=float, default=1.0, help="stop the run at this many USD")
    a = ap.parse_args()

    if a.input:
        run_input = json.load(open(a.input, encoding="utf-8"))
    else:
        run_input = {"maxJobs": a.max}
        if a.keyword:
            run_input["queries"] = a.keyword
        if a.city:
            run_input["locations"] = a.city
        if a.days:
            run_input["postedWithinDays"] = a.days
        if a.only_new:
            run_input.update({"onlyNewSinceLastRun": True, "stateName": a.only_new})

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN (Apify Console > Settings > Integrations).")
    client = ApifyClient(token)
    run = client.actor(ACTOR).call(run_input=run_input, max_total_charge_usd=a.max_cost)
    if run is None or run.get("status") != "SUCCEEDED":
        sys.exit(f"Run did not succeed: {run and run.get('status')} {run and run.get('statusMessage')}")
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    with open(a.out + ".json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    with open(a.out + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for it in items:
            w.writerow([flat(it.get(c)) for c in CSV_COLUMNS])
    print(f"{len(items)} jobs -> {a.out}.json, {a.out}.csv  (run {run['id']}: {run.get('statusMessage', '')})")


if __name__ == "__main__":
    main()
