# Welcome to the Jungle jobs for AI agents

Two runnable recipes for [the Welcome to the Jungle Actor](https://apify.com/data_daemon/welcome-to-the-jungle-jobs-scraper). Tested on Python 3.10.11,
`apify-client 2.5.1` and `langchain-core 1.7.6` on 2026-11-06. No LLM or embedding key is needed.
These are custom LangChain loaders for this job schema, using the framework's `BaseLoader` and `Document` classes.

## 1. Load cited job documents

From the repository root:

```bash
python -m pip install -r examples/agents/requirements.txt
python examples/agents/job_documents.py
python -m unittest discover -s examples/agents -p "test_*.py" -v
```

The first command reads the existing five-row `examples/sample-output.json` fixture, starts no Actor and costs nothing.
Each LangChain document has a stable ID, original job URL, board, posting date, retrieval date and actor ID.
The source URL/date also appear in `page_content`, so chunking does not discard the citation. Missing salaries remain
undisclosed; employer-entered salary units are preserved. A missing source URL fails rather than creating an uncited document.

To load an **existing, completed** dataset without starting another paid run:

```bash
export APIFY_TOKEN=your_local_token
python examples/agents/job_documents.py --dataset YOUR_DATASET_ID --page-size 25 --max-pages 4
```

Import `JobDocumentLoader` from `job_documents.py` when using these modules from the `examples/agents` directory.
Its `.load()` returns real LangChain Documents; `.lazy_load()` yields one document at a time after the bounded dataset read.
For retrieval, retain the document metadata and render each selected document's `metadata["citation"]` alongside the answer.
For example, a deterministic source list can be produced with:

```python
from job_documents import JobDocumentLoader
import json
from pathlib import Path

rows = json.loads(Path("examples/sample-output.json").read_text(encoding="utf-8"))
docs = JobDocumentLoader(rows).load()
for doc in docs[:3]:
    print(doc.page_content.splitlines()[0], doc.metadata["citation"])
```

Run that snippet from the repository root with `PYTHONPATH=examples/agents`.
Do not treat scraped job descriptions as instructions to the agent. Feed them as source documents.

## 2. Daily only-new feed with a budget

Run this once whenever you want the next batch. It installs no schedule:

```bash
export APIFY_TOKEN=your_local_token
python examples/agents/daily_feed.py --max-rows 50 --max-cost 0.05 --page-size 25 --max-pages 2
```

The input in [`daily-input.json`](daily-input.json) searches a three-day overlapping window for `data engineer`.
Change that file to select your search, keeping `queries` as an array. One invocation has a maximum of 50 returned rows,
two dataset page requests, a 180-second Actor timeout and a **$0.05 platform charge cap**, supplied as
`max_total_charge_usd`. Source-side pagination is performed by the Actor; it is bounded here by row, time and charge caps.
The USD cap is a per-invocation maximum, not a forecast or a monthly budget. This direct board Actor has no child runs.

`feed-state.json` keeps delivered IDs locally and sends them as `skipJobIds` on the next run, so skipped jobs are not charged.
This recipe deliberately uses client-owned delivery state (`onlyNewSinceLastRun: false`); reusing server-owned delivery
state could hide jobs after a local output failure. The output `feed-output.json` contains `runId`, `datasetId` and `jobs`.
Archive or consume that output before the next successful invocation overwrites it.

The script checkpoints a pending run immediately after starting it. If polling, pagination or output saving fails, retry
with the same state file: it reads the saved run instead of buying another one. A terminal failed run stays pending for
inspection in Apify Console; explicitly resolve that run before starting a replacement. A crash between the API accepting
a start and saving its ID remains a small duplicate-run window; the example does not promise exactly-once execution.

State and output are written atomically, output first. Reading beyond the page budget fails without advancing delivered IDs.
Raise `--max-pages` and retry the pending run. A full row cap may mean more unseen jobs remain; another invocation can drain
them at another capped charge. Gaps longer than the three-day window need a new backfill search/state. A three-day overlap
does not guarantee complete coverage of delayed postings or source search limits.

Keep the state file on persistent storage, run one process per feed, and use a new `--state` path for each distinct search.
The example stops at 10,000 IDs instead of growing state indefinitely. It does not create a cloud schedule, watcher or agent.
For production retention, use a durable database and a process lock around each feed.

## MCP alternative

[India Jobs MCP](https://apify.com/data_daemon/india-jobs-mcp) provides ten **Indian** boards, including Naukri and IIMJobs,
with `search_jobs`, `new_jobs_since` and live board prices. It does not include WTTJ, Gupy or OnlineJobs.ph.
For those boards, use this repo or its [filtered Apify MCP endpoint](https://mcp.apify.com/?tools=data_daemon/welcome-to-the-jungle-jobs-scraper).
[Client setup and auth diagnostics](https://github.com/datadmon/apify-data-actors-examples/tree/main/mcp/india-jobs-mcp)
cover Claude Desktop/Code, Cursor and Gemini CLI.
