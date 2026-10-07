# Crude oil

[![ci](https://github.com/accomplish999/crude-oil/actions/workflows/ci.yml/badge.svg)](https://github.com/accomplish999/crude-oil/actions/workflows/ci.yml)

Public prices, stocks, and positions for crude. WTI is EIA `RWTC`. Brent is EIA `RBRTE`. The weekly barrel count is the Weekly Petroleum Status Report workbook EIA posts, not a redraw. NYMEX contracts 1 through 4 are the four series EIA publishes. Managed money is the CFTC disaggregated futures report, contracts `067651` (WTI-PHYSICAL, NYMEX) and `06765T` (Brent last day, NYMEX).

Every stored point keeps its source file, its series key, and the day the file was fetched. A blank cell stays blank. Nothing on the site is filled across a gap.

Past prices do not predict future prices. This is not financial advice. A futures contract can wipe out the account that trades it.

## What you can do with it

The site is one page.

- Filter the sheet by date, series, and regime. Frozen header, per-column filters, sort, and a formula column (`LAG`, `LOG`, `ABS`). Export the view as CSV, JSON, or Parquet. Full books are also at `public/downloads/`.
- Read the walk-forward studies. The split is fixed: train through 31 Dec 2019, holdout from 1 Jan 2020. The same text is a Jupyter notebook in `notebooks/`.
- Derived columns (days of cover, curve z, COT z, crack gap, realized vol, and the rest) carry a formula and a holdout result. Held means the precommitted bar was met. It is not a trade.
- Size a CL, MCL, or BZ position from tick value, a margin you type in, and a close-to-close volatility sample. The archive does not store a live margin.
- Ask the chat about the archive. Off-topic questions and attempts to rewrite the rules are refused. With `GEMINI_API_KEY` set, Gemini must call tools and the page shows the rows. With no key, the same tools answer locally and say so. There is no web search. The key stays on the server.

## Run it

Node 20 or newer. Python 3.11 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/ingest.py
.venv/bin/python scripts/studies.py
npm install
npm run dev
```

The committed `data/` tree is a full snapshot, so the site builds without a fresh download. `npm run check` scans for em dashes, runs lint, builds, checks links, and re-fetches the sources to compare values.

Copy `.env.example` to `.env.local` and set `GEMINI_API_KEY` if you want the model. The key stays on the server. Do not commit it.

## Data

Sources, licenses, and the series that are linked rather than stored are in [docs/provenance.md](docs/provenance.md).

```bash
.venv/bin/python scripts/ingest.py
.venv/bin/python scripts/studies.py
```

GitHub Actions refreshes on weekdays, again on Wednesday around the EIA release, and on Friday around the CFTC release. `scripts/verify.py` has to pass before a commit. A failed run opens a GitHub issue titled `Data refresh failed` and does not change `main`. See `.github/workflows/refresh.yml` and `CHANGELOG.md`.

## Deploy

The app is a Next.js server because the chat route has to run where the key is. Static hosting cannot answer `/api/chat`. The path on [accompli.sh/crude-oil](https://accompli.sh/crude-oil) is a rewrite in the parent project. The exact rule, and the reason `/research` currently 404s, is in [docs/deploy.md](docs/deploy.md).

## License

MIT. Copyright (c) 2026 crude oil contributors.

The price and position files are US government work and are public domain. This repository's code is MIT. See provenance before you republish a series that did not come from EIA, FRED, or the CFTC.
