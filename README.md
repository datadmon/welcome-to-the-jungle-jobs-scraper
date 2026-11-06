# Welcome to the Jungle Scraper (Python): WTTJ jobs to JSON and CSV

[![Run on Apify](https://img.shields.io/badge/Run%20on-Apify-00A67E?logo=apify&logoColor=white)](https://apify.com/data_daemon/welcome-to-the-jungle-jobs-scraper)
![Output](https://img.shields.io/badge/output-JSON%20%7C%20CSV%20%7C%20Excel-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Scrape **Welcome to the Jungle (WTTJ) jobs** into JSON or CSV from Python: title, company with size and sector, offices, country, contract type, remote mode, salary when published, experience and education level, skills, tools and the **full job description**. Filter by keyword, country, city, contract type and remote mode.

[Welcome to the Jungle](https://www.welcometothejungle.com/en/jobs) is the France-focused job board for startups and tech companies. This repository is a small, tested Python client for the hosted
**[Welcome to the Jungle Jobs Scraper | WTTJ API & New Job Feed](https://apify.com/data_daemon/welcome-to-the-jungle-jobs-scraper)** on Apify: no browser, proxy, login or scraper maintenance on your side. Price:
**$0.80 per 1,000 jobs, full description included, plus $0.001 per run**; Apify's free plan ($5 of credit every month) covers about 6,000 jobs.

## Quick start

```bash
pip install apify-client
export APIFY_TOKEN=your_token      # Apify Console > Settings > Integrations
python scrape.py --keyword "data engineer" --max 50
```

`scrape.py` starts the Actor, waits for it and writes `welcome-jobs.json` (every field) and `welcome-jobs.csv`
(the main columns). For any other option, put the Actor input in a file and pass `--input`:

```bash
python scrape.py --input examples/input.json
```

```json
{
  "queries": [
    "data engineer"
  ],
  "countryCodes": [
    "FR"
  ],
  "maxJobs": 5
}
```

## Sample output

A real run of [`examples/input.json`](examples/input.json) on 5 November 2026
([full JSON](examples/sample-output.json), [CSV](examples/sample-output.csv); descriptions shortened):

| postedAt | title | company | locations | contractType | remoteMode |
|---|---|---|---|---|---|
| 2026-11-05 | Data Engineer Databricks / AWS / Spark (H/F) | skiils | Suresnes, FR, Lille, FR | full_time | partial |
| 2026-11-05 | Product Manager Data / Analytics Engineer (H/F) | Hubvisory | Paris, FR | full_time | partial |
| 2026-11-04 | Data Engineer BI (H/F) | Culligan | Versailles, FR | full_time | unknown |
| 2026-11-04 | Consultant(e) Data Engineer F/H | CGI | Nantes, FR | full_time | partial |
| 2026-11-04 | Data Quality Engineer (h/f/x) | Hager | Obernai, FR | full_time | partial |

## Output fields

| Field | Description |
|---|---|
| `id` | Public job reference, or source search ID if a reference is absent. |
| `sourceId` | Search index object ID, as a string. |
| `dedupKey` | Stable `wttj:` prefix plus job ID, useful in multi-source databases. |
| `url`, `applyUrl` | Canonical public page and external application link when provided. |
| `title`, `slug` | Job title and public URL slug. |
| `company` | Public name, slug, reference, website, headcount, size, founding year, logo, industry and headquarters when available. |
| `locations`, `offices`, `countryCodes` | Office labels, structured city/region/country/coordinates, and country codes. |
| `remoteMode`, `contractType`, `language` | Source remote, contract and posting-language labels. |
| `salary` | Minimum, maximum, currency, period and source yearly minimum; all amounts are preserved as provided. |
| `experienceLevel`, `educationLevel` | Source experience and education labels when stated. |
| `profession` | Public profession label and company sector labels when supplied. |
| `sectors` | Company sector labels when supplied. |
| `postedAt`, `updatedAt`, `startDate` | Source dates in ISO format when available. |
| `skills` | Job skill labels in English when the source provides them, otherwise French. |
| `tools` | Named tools and technologies the employer lists, such as Python. |
| `description` | Full description as HTML and plain text; null in listing-only mode. |
| `candidateProfile`, `recruitmentProcess` | Plain-text candidate requirements and interview process when published. |
| `query` | First search keyword that delivered this job. |
| `source`, `scrapedAt` | Source label and collection timestamp. |

<!-- agent-recipes:start -->
## Use with AI agents

Load [Welcome to the Jungle jobs](https://apify.com/data_daemon/welcome-to-the-jungle-jobs-scraper) as **cited LangChain documents**, or run a daily only-new feed
with bounded pagination and a USD charge cap. Both [runnable recipes](examples/agents/README.md) include offline fixtures,
failure/resume tests and pinned dependencies; no LLM key is needed.
[India Jobs MCP](https://apify.com/data_daemon/india-jobs-mcp) is the ten-Indian-board alternative for agents
(WTTJ, Gupy and OnlineJobs.ph use their own filtered Apify MCP endpoints).
<!-- agent-recipes:end -->

## Daily feed of only new jobs

```bash
python scrape.py --keyword "data engineer" --only-new welcome-daily --max 0
```

With `--only-new <name>` the Actor remembers which jobs it has delivered under that name and returns only new ones;
skipped jobs are not charged. Run it from cron, a GitHub Actions schedule or an Apify schedule:

```yaml
# .github/workflows/welcome-daily.yml
on:
  schedule: [{cron: "30 2 * * *"}]
  workflow_dispatch:
jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install apify-client && python scrape.py --keyword "data engineer" --only-new welcome-daily --max 0
        env: {APIFY_TOKEN: "${{ secrets.APIFY_TOKEN }}"}
      - uses: actions/upload-artifact@v4
        with: {name: welcome-jobs, path: "welcome-jobs.*"}
```

## Other ways to call it

**curl**, one request that runs the Actor and returns the rows:

```bash
curl -X POST "https://api.apify.com/v2/acts/data_daemon~welcome-to-the-jungle-jobs-scraper/run-sync-get-dataset-items" \
  -H "Authorization: Bearer $APIFY_TOKEN" -H "Content-Type: application/json" \
  -d '{"queries": ["data engineer"], "countryCodes": ["FR"], "maxJobs": 5}'
```

**Apify CLI:** `apify call data_daemon/welcome-to-the-jungle-jobs-scraper --input-file examples/input.json`

**No code:** open the [Actor page](https://apify.com/data_daemon/welcome-to-the-jungle-jobs-scraper), fill the form and export to CSV/Excel, or connect it to Google Sheets,
Zapier, Make or n8n. AI agents can call it through the Apify MCP server (`https://mcp.apify.com`).

## FAQ

### Does Welcome to the Jungle have a jobs API?

Welcome to the Jungle's Welcome Kit API is for employers managing their own postings and candidates; it does not search other companies' jobs. This repo calls a hosted Apify Actor that reads WTTJ's public job search.

### Which countries does it cover?

The public, France-focused WTTJ board, including its jobs in other countries (not the separate Otta / US / UK matching inventory). Filter by office country with two-letter codes in `countryCodes`, for example `FR`, `ES` or `DE`.

### Can I watch only new WTTJ jobs?

Yes: `scrape.py --only-new my-feed` on a daily schedule returns only jobs not delivered to that feed before; skipped jobs are free.

### Is it legal to scrape Welcome to the Jungle?

The Actor reads only public job listings, without logging in, at a polite request rate, and returns job and company
data, not personal profiles. Check the rules that apply to your use of the data in your jurisdiction.

## Related

- [Career Site Jobs API – Workday, Greenhouse, Lever, Ashby](https://apify.com/data_daemon/career-site-jobs-scraper)
- [Oracle Jobs Scraper – Oracle HCM & Recruiting Cloud Career Site](https://apify.com/data_daemon/oracle-hcm-jobs-scraper)
- [Gupy Jobs Scraper | Brazil Jobs with Descriptions (Gupy Portal)](https://apify.com/data_daemon/gupy-jobs-scraper)
- [India Job Alerts](https://github.com/datadmon/india-job-alerts): new jobs from seven Indian boards every morning via GitHub Actions
- [All Daemon Data Actors](https://apify.com/data_daemon)

Unofficial project, not affiliated with Welcome to the Jungle. Issues and questions: open an issue here or on the
[Actor's Issues tab](https://apify.com/data_daemon/welcome-to-the-jungle-jobs-scraper/issues).
