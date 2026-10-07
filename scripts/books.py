#!/usr/bin/env python3
"""Build the sheet books. Cells are stored prints or labeled derived values. Blanks stay blank."""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logic import HOLDOUT_START, adjacent_log_returns, canon_number, mad_scale, mean, pairs, weekly_changes  # noqa: E402

SERIES = ROOT / "data" / "series"
OUT = ROOT / "data" / "books"


def load(series_id: str) -> dict:
    return json.loads((SERIES / f"{series_id}.json").read_text())


def value_map(series_id: str, field: str = "value") -> tuple[dict, dict[str, str]]:
    series = load(series_id)
    values = {}
    for row in series["observations"]:
        if field not in row:
            continue
        values[row["date"]] = row[field]
    meta = {
        "unit": series["unit"],
        "source": series["source"],
        "source_url": series.get("source_url") or series.get("download_url") or "",
        "retrieved_at": series["retrieved_at"],
        "derived": series["derived"],
        "method": series.get("method") or "",
    }
    return values, meta


def return_z(series_id: str) -> dict[str, str]:
    rows = pairs(load(series_id))
    rets = adjacent_log_returns(rows)
    train = [item["log_return"] for item in rets if item["date"] < HOLDOUT_START]
    if len(train) < 30:
        return {}
    center, scale = mad_scale(train)
    if scale == 0:
        return {}
    return {
        item["date"].isoformat(): canon_number((item["log_return"] - center) / scale)
        for item in rets
    }


def change_z(series_id: str) -> dict[str, str]:
    changes = weekly_changes(pairs(load(series_id)))
    train = [item["change"] for item in changes if item["date"] < HOLDOUT_START]
    if len(train) < 30:
        return {}
    center, scale = mad_scale(train)
    if scale == 0:
        return {}
    return {
        item["date"].isoformat(): canon_number((item["change"] - center) / scale)
        for item in changes
    }


def level_z(series_id: str, field: str = "value") -> dict[str, str]:
    values, _ = value_map(series_id, field)
    train = [float(value) for day, value in values.items() if date.fromisoformat(day) < HOLDOUT_START]
    if len(train) < 30:
        return {}
    center = mean(train)
    scale = statistics.pstdev(train)
    if center is None or scale == 0:
        return {}
    return {
        day: canon_number((float(value) - center) / scale)
        for day, value in values.items()
    }


def column(key: str, label: str, meta: dict, formula: str, zed: bool) -> dict:
    return {
        "key": key,
        "label": label,
        "unit": meta["unit"],
        "derived": bool(meta["derived"]),
        "formula": formula or meta["method"],
        "source": meta["source"],
        "source_url": meta["source_url"],
        "retrieved_at": meta["retrieved_at"],
        "z": zed,
    }


def build(book_id: str, name: str, specs: list[dict]) -> dict:
    maps = []
    columns = []
    zmaps = []
    dates = set()
    for spec in specs:
        values, meta = value_map(spec["series"], spec.get("field", "value"))
        maps.append(values)
        dates.update(values)
        if spec.get("unit"):
            meta = {**meta, "unit": spec["unit"]}
        columns.append(column(spec["key"], spec["label"], meta, spec.get("formula", ""), spec.get("z") is not None))
        zmaps.append(spec["z"] if spec.get("z") else {})
    ordered = sorted(dates)
    rows = []
    z_rows = []
    for day in ordered:
        row = [day]
        z_row = [None]
        for values, zed in zip(maps, zmaps):
            row.append(values.get(day, ""))
            z_row.append(zed.get(day) if values.get(day, "") else None)
        rows.append(row)
        z_rows.append(z_row)
    date_col = {
        "key": "date",
        "label": "Date",
        "unit": "",
        "derived": False,
        "formula": "Publication date on the source file.",
        "source": "",
        "source_url": "",
        "retrieved_at": "",
        "z": False,
    }
    return {
        "id": book_id,
        "name": name,
        "columns": [date_col, *columns],
        "rows": rows,
        "z": z_rows,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rwtc_z = return_z("RWTC")
    brent_z = return_z("RBRTE")
    books = [
        build(
            "prices",
            "Prices",
            [
                {"key": "RWTC", "series": "RWTC", "label": "WTI", "z": rwtc_z, "formula": "EIA RWTC, dollars per barrel. z is the adjacent log return against the train median and 1.4826 times the train MAD. Train ends 31 Dec 2019."},
                {"key": "RBRTE", "series": "RBRTE", "label": "Brent", "z": brent_z, "formula": "EIA RBRTE. z uses the same robust scale on Brent's own adjacent log returns."},
                {"key": "RCLC1", "series": "RCLC1", "label": "CL1", "formula": "EIA NYMEX crude futures contract 1. The workbook history ends before the spot series."},
                {"key": "RCLC4", "series": "RCLC4", "label": "CL4", "formula": "EIA NYMEX crude futures contract 4."},
                {"key": "CL1_MINUS_CL4", "series": "CL1_MINUS_CL4", "label": "CL1-CL4", "z": level_z("CL1_MINUS_CL4"), "formula": "RCLC1 minus RCLC4. Positive means the front is above the fourth. z is a level z-score against the train mean and train population standard deviation."},
                {"key": "CURVE_Z", "series": "CURVE_Z", "label": "Curve z", "formula": ""},
                {"key": "CRACK_321", "series": "CRACK_321", "label": "Crack", "formula": "((2 * RBOB futures + heating oil futures) / 3) * 42 minus CL1."},
                {"key": "CRACK_GAP", "series": "CRACK_GAP", "label": "Crack gap", "formula": ""},
                {"key": "RV20", "series": "RV20", "label": "RV20", "formula": ""},
                {"key": "HO_SPOT", "series": "HO_SPOT", "label": "Heat", "formula": "EIA New York Harbor No. 2 heating oil spot, dollars per gallon."},
                {"key": "GAS_SPOT", "series": "GAS_SPOT", "label": "Gasoline", "formula": "EIA New York Harbor conventional gasoline spot, dollars per gallon."},
                {"key": "DTWEXBGS", "series": "DTWEXBGS", "label": "Dollar", "formula": "FRED broad dollar index, goods and services."},
                {"key": "DGS10", "series": "DGS10", "label": "10y", "formula": "FRED 10-year Treasury yield, percent."},
                {"key": "DGS2", "series": "DGS2", "label": "2y", "formula": "FRED 2-year Treasury yield, percent."},
                {"key": "DGS10_MINUS_DGS2", "series": "DGS10_MINUS_DGS2", "label": "10y-2y", "formula": "DGS10 minus DGS2."},
            ],
        ),
        build(
            "weekly",
            "Weekly",
            [
                {"key": "WCESTUS1", "series": "WCESTUS1", "label": "Crude ex-SPR", "z": change_z("WCESTUS1"), "formula": "EIA commercial crude stocks, thousand barrels. z is the 7-day change against the train median and MAD."},
                {"key": "CUSHING", "series": "CUSHING", "label": "Cushing", "z": change_z("CUSHING"), "formula": "EIA Cushing stocks excluding SPR, thousand barrels. z is the 7-day change against the train median and MAD."},
                {"key": "CUSHING_COVER", "series": "CUSHING_COVER", "label": "Days cover", "formula": ""},
                {"key": "WCSSTUS1", "series": "WCSSTUS1", "label": "SPR", "formula": "EIA Strategic Petroleum Reserve, thousand barrels."},
                {"key": "SPR_FLOW", "series": "SPR_FLOW", "label": "SPR change", "formula": ""},
                {"key": "INV_SURPRISE", "series": "INV_SURPRISE", "label": "Surprise", "formula": ""},
                {"key": "SEAS_STOCK", "series": "SEAS_STOCK", "label": "Seasonal stock", "formula": ""},
                {"key": "WPULEUS3", "series": "WPULEUS3", "label": "Utilization", "formula": "EIA refinery utilization, percent."},
                {"key": "UTIL_DEV", "series": "UTIL_DEV", "label": "Util gap", "formula": ""},
                {"key": "WCRFPUS2", "series": "WCRFPUS2", "label": "Production", "formula": "EIA weekly field production, thousand barrels per day."},
                {"key": "WCRRIUS2", "series": "WCRRIUS2", "label": "Inputs", "formula": "EIA refiner net inputs of crude, thousand barrels per day."},
                {"key": "WCRIMUS2", "series": "WCRIMUS2", "label": "Imports", "formula": "EIA crude imports, thousand barrels per day."},
                {"key": "WCREXUS2", "series": "WCREXUS2", "label": "Exports", "formula": "EIA crude exports, thousand barrels per day."},
                {"key": "WCRSTUS1", "series": "WCRSTUS1", "label": "Total crude", "formula": "EIA total US crude stocks, thousand barrels."},
                {"key": "WDISTUS1", "series": "WDISTUS1", "label": "Distillate", "formula": "EIA distillate stocks, thousand barrels."},
                {"key": "WGTSTUS1", "series": "WGTSTUS1", "label": "Gasoline stocks", "formula": "EIA gasoline stocks, thousand barrels."},
            ],
        ),
        build(
            "positions",
            "Positions",
            [
                {"key": "CL_OI", "series": "CFTC_CL", "field": "open_interest", "label": "CL open interest", "formula": "CFTC 067651 open interest, futures only."},
                {"key": "CL_MM_NET", "series": "CFTC_CL", "field": "mm_net", "label": "CL managed net", "formula": "Managed money long minus short. Spreads are not included."},
                {"key": "CL_MM_OI", "series": "CFTC_CL", "field": "mm_net_oi", "label": "CL net / OI", "unit": "ratio", "z": level_z("CFTC_CL", "mm_net_oi"), "formula": "Managed money net divided by open interest. z uses the train mean and train population standard deviation of this ratio."},
                {"key": "COT_Z", "series": "COT_Z", "label": "COT z", "formula": ""},
                {"key": "COT_PCT", "series": "COT_PCT", "label": "COT percentile", "formula": ""},
                {"key": "CL_MM_LONG", "series": "CFTC_CL", "field": "mm_long", "label": "CL managed long", "formula": "CFTC 067651 managed money long."},
                {"key": "CL_MM_SHORT", "series": "CFTC_CL", "field": "mm_short", "label": "CL managed short", "formula": "CFTC 067651 managed money short."},
                {"key": "BRENT_OI", "series": "CFTC_BRENT", "field": "open_interest", "label": "Brent open interest", "formula": "CFTC 06765T open interest."},
                {"key": "BRENT_MM_NET", "series": "CFTC_BRENT", "field": "mm_net", "label": "Brent managed net", "formula": "CFTC 06765T managed money long minus short."},
                {"key": "BRENT_MM_OI", "series": "CFTC_BRENT", "field": "mm_net_oi", "label": "Brent net / OI", "unit": "ratio", "formula": "CFTC 06765T managed money net divided by open interest."},
            ],
        ),
    ]
    index = {"books": [], "z_rule": "A z cell uses train data through 31 Dec 2019. |z| above 4 matches the anomaly flag on RWTC returns. Blank input, blank z."}
    for book in books:
        path = OUT / f"{book['id']}.json"
        path.write_text(json.dumps(book, separators=(",", ":")) + "\n")
        index["books"].append({"id": book["id"], "name": book["name"], "rows": len(book["rows"]), "columns": len(book["columns"])})
        print(f"{book['id']}: {len(book['rows'])} rows, {len(book['columns'])} columns")
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
