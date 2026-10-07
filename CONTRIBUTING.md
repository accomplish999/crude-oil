# Contributing

The archive is the product. A pull request that adds a number has to show the file it came from.

## Rules

- No em dashes (U+2014) in code, copy, JSON, or docs. `npm run check:dashes` fails the build.
- Do not invent a print, a stock, or a position. If the cell is empty, leave it empty and count the skip.
- Do not change the holdout date (`2020-01-01`) or a frozen threshold to make a study look better. If you find a bug in the alignment, fix the bug and say what moved.
- Derived fields (a crack, a net position, a spread) carry `derived: true` and the exact inputs. They are not source series.
- Keep licenses straight. EIA, FRED, and CFTC files in this repo are US government works. OPEC monthly reports, IEA tables, Baker Hughes rig counts, and exchange quote feeds are not mirrored here. Link them.
- Never commit `.env`, `.env.local`, or an API key.
- Copy stays specific. Name the series key, the unit, and the window. Skip slogans.

## Checks

```bash
.venv/bin/python scripts/ingest.py
.venv/bin/python scripts/studies.py
.venv/bin/python -m unittest scripts/test_logic.py
npm run check
```

`scripts/verify.py` re-downloads the workbooks and the current CFTC file and compares them to `data/`. A mismatch is a failed check, not a warning.

## Refresh

Weekly refresh is `.github/workflows/refresh.yml`. If you add a series, add it to `scripts/catalog.py` and to the cross-check list in `scripts/verify.py` when a second public file of the same print exists.
