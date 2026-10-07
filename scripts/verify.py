#!/usr/bin/env python3
"""Re-download sources and compare them to data/series.

EIA workbooks and FRED csv files are compared row for row.
FRED DCOILWTICO and DCOILBRENTEU are compared to RWTC and RBRTE on shared dates.
The current CFTC file is compared to the latest stored row for 067651 and 06765T.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog import CFTC_CODES, EIA_XLS, FRED, FRED_CROSSCHECK  # noqa: E402
from ingest import (  # noqa: E402
    CFTC_CURRENT,
    fetch,
    iso_date,
    read_eia,
    read_fred,
    rows_from_cftc_text,
)
from logic import canon_number  # noqa: E402

SERIES = ROOT / "data" / "series"


def stored(series_id: str) -> dict:
    return json.loads((SERIES / f"{series_id}.json").read_text())


def same_rows(series_id: str, fresh: list[dict]) -> None:
    current = stored(series_id)["observations"]
    if len(current) != len(fresh):
        raise SystemExit(f"{series_id} count {len(current)} != source {len(fresh)}")
    for index, (left, right) in enumerate(zip(current, fresh)):
        if left["date"] != right["date"] or left["value"] != right["value"]:
            raise SystemExit(f"{series_id} row {index} {left} != {right}")


def cross_check(series_id: str, fred_id: str) -> None:
    fresh = {row["date"]: row["value"] for row in read_fred(fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}"), fred_id)}
    local = {row["date"]: row["value"] for row in stored(series_id)["observations"]}
    shared = sorted(set(fresh) & set(local))
    if len(shared) < 100:
        raise SystemExit(f"{series_id} vs {fred_id} shared dates {len(shared)}")
    mismatches = []
    for day in shared:
        if abs(float(fresh[day]) - float(local[day])) > 1e-6:
            mismatches.append((day, local[day], fresh[day]))
    if mismatches:
        raise SystemExit(f"{series_id} vs {fred_id} mismatch {mismatches[:5]}")
    print(f"cross {series_id} {fred_id} {len(shared)} dates")


def cftc_latest() -> None:
    text = fetch(CFTC_CURRENT).decode("latin-1")
    # Build a map from any headed annual file already reflected in stored rows by
    # reusing the current file if it has a header, else a positional map from
    # the 2024 zip is loaded inside ingest. Here we demand a header or the
    # known short layout.
    column_map, hits = rows_from_cftc_text(text, None) if "Market_and_Exchange" in text.splitlines()[0] else (None, None)
    if hits is None:
        from ingest import header_map

        # Current combined file is headerless. Column order matches the annual header.
        sample = fetch("https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip")
        import io
        import zipfile

        archive = zipfile.ZipFile(io.BytesIO(sample))
        member = next(name for name in archive.namelist() if name.lower().endswith((".txt", ".csv")))
        headed = archive.read(member).decode("latin-1")
        column_map, _ = rows_from_cftc_text(headed, None)
        _, hits = rows_from_cftc_text(text, column_map)
    by_code = {}
    for hit in hits:
        by_code.setdefault(hit["code"], hit)
    for code, meta in CFTC_CODES.items():
        hit = by_code.get(code)
        if not hit:
            raise SystemExit(f"current CFTC file missing {code}")
        series = stored(meta["id"])
        last = series["observations"][-1]
        if last["date"] != hit["date"]:
            raise SystemExit(f"{meta['id']} last {last['date']} != current {hit['date']}")
        for key in ("open_interest", "mm_long", "mm_short", "mm_net"):
            if last[key] != hit[key]:
                raise SystemExit(f"{meta['id']} {key} stored {last[key]} != source {hit[key]}")
        print(f"cftc {meta['id']} {hit['date']} oi {hit['open_interest']}")


def main() -> None:
    for spec in EIA_XLS:
        url = "https://www.eia.gov/dnav/pet/hist_xls/" + spec["file"]
        print("verify", spec["id"])
        _, rows = read_eia(fetch(url))
        same_rows(spec["id"], rows)
    for spec in FRED:
        print("verify", spec["id"])
        rows = read_fred(fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + spec["id"]), spec["id"])
        same_rows(spec["id"], rows)
    for series_id, fred_id in FRED_CROSSCHECK.items():
        cross_check(series_id, fred_id)
    cftc_latest()
    # Derived series must match the arithmetic. Recompute a sample of the crack.
    crack = stored("CRACK_321")
    rbob = {row["date"]: row["value"] for row in stored("RBOB_F1")["observations"]}
    heat = {row["date"]: row["value"] for row in stored("HO_F1")["observations"]}
    crude = {row["date"]: row["value"] for row in stored("RCLC1")["observations"]}
    for row in crack["observations"][:: max(1, len(crack["observations"]) // 50)]:
        day = row["date"]
        expected = canon_number(((2 * float(rbob[day]) + float(heat[day])) / 3) * 42 - float(crude[day]))
        if expected != row["value"]:
            raise SystemExit(f"crack {day} {row['value']} != {expected}")
    print("verify ok")


if __name__ == "__main__":
    main()
