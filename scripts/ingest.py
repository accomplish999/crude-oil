#!/usr/bin/env python3
"""Download public EIA, FRED, and CFTC files and write data/series.

Blank cells are skipped. Derived series are arithmetic on dates where every
input exists. Retrieval time is UTC.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import xlrd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from catalog import (  # noqa: E402
    CFTC_CODES,
    CFTC_YEARS,
    EIA_XLS,
    FRED,
    USER_AGENT,
)
from logic import canon_number  # noqa: E402

SERIES_DIR = ROOT / "data" / "series"
RAW_DIR = ROOT / "data" / "raw"
EIA_BASE = "https://www.eia.gov/dnav/pet/hist_xls/"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
CFTC_CURRENT = "https://www.cftc.gov/dea/newcot/c_disagg.txt"
CFTC_ZIP = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=90) as response:
        return response.read()


def sheet_meta(book: xlrd.book.Book) -> dict:
    sheet = book.sheet_by_index(0)
    meta = {
        "title": "",
        "release_date": "",
        "next_release": "",
        "source_page": "",
        "source_key": "",
    }
    for row in range(sheet.nrows):
        label = str(sheet.cell_value(row, 1)).strip() if sheet.ncols > 1 else ""
        value = str(sheet.cell_value(row, 2)).strip() if sheet.ncols > 2 else ""
        if row == 2 and label:
            meta["title"] = label
        if label == "Release Date:":
            meta["release_date"] = value
        elif label == "Next Release Date:":
            meta["next_release"] = value
        elif label == "Available from Web Page:":
            meta["source_page"] = value
    return meta


def read_eia(blob: bytes) -> tuple[dict, list[dict]]:
    book = xlrd.open_workbook(file_contents=blob)
    meta = sheet_meta(book)
    data = book.sheet_by_name("Data 1")
    meta["source_key"] = str(data.cell_value(1, 1)).strip()
    column = str(data.cell_value(2, 1)).strip()
    meta["column"] = column
    rows = []
    for index in range(3, data.nrows):
        date_cell = data.cell(index, 0)
        value_cell = data.cell(index, 1)
        if date_cell.ctype != xlrd.XL_CELL_DATE:
            continue
        if value_cell.ctype != xlrd.XL_CELL_NUMBER:
            continue
        stamp = xlrd.xldate_as_datetime(date_cell.value, book.datemode).date()
        rows.append({"date": stamp.isoformat(), "value": canon_number(value_cell.value)})
    return meta, rows


def read_fred(blob: bytes, series_id: str) -> list[dict]:
    text = blob.decode("utf-8")
    rows = []
    for record in csv.DictReader(io.StringIO(text)):
        raw = (record.get(series_id) or "").strip()
        if raw in {"", "."}:
            continue
        rows.append({"date": record["observation_date"], "value": raw})
    return rows


def write_series(payload: dict) -> None:
    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    path = SERIES_DIR / f"{payload['id']}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")


def base_payload(spec: dict, rows: list[dict], retrieved_at: str) -> dict:
    return {
        "id": spec["id"],
        "name": spec["name"],
        "unit": spec.get("unit", ""),
        "frequency": spec["frequency"],
        "group": spec["group"],
        "source": spec["source"],
        "source_key": spec.get("source_key", spec["id"]),
        "source_url": spec["source_url"],
        "download_url": spec["download_url"],
        "license": "US government public domain",
        "retrieved_at": retrieved_at,
        "release_date": spec.get("release_date", ""),
        "next_release": spec.get("next_release", ""),
        "derived": False,
        "method": "",
        "inputs": [],
        "fields": [
            {
                "key": "value",
                "name": spec["name"],
                "unit": spec.get("unit", ""),
                "derived": False,
            }
        ],
        "observations": rows,
    }


def unit_from_title(title: str) -> str:
    if "Dollars per Gallon" in title:
        return "dollars per gallon"
    if "Dollars per Barrel" in title:
        return "dollars per barrel"
    if "Thousand Barrels per Day" in title:
        return "thousand barrels per day"
    if "Thousand Barrels" in title:
        return "thousand barrels"
    if "(Percent)" in title:
        return "percent"
    return ""


def ingest_eia(retrieved_at: str) -> list[str]:
    ids = []
    for spec in EIA_XLS:
        url = EIA_BASE + spec["file"]
        print(f"EIA {spec['id']} {url}")
        blob = fetch(url)
        meta, rows = read_eia(blob)
        if len(rows) < 10:
            raise SystemExit(f"{spec['id']} returned {len(rows)} rows")
        payload = base_payload(
            {
                **spec,
                "name": meta["title"] or meta["column"],
                "unit": unit_from_title(meta["title"]),
                "source": "EIA",
                "source_key": meta["source_key"],
                "source_url": meta["source_page"]
                or f"https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s={meta['source_key']}&f=D",
                "download_url": url,
                "release_date": meta["release_date"],
                "next_release": meta["next_release"],
            },
            rows,
            retrieved_at,
        )
        write_series(payload)
        ids.append(spec["id"])
    return ids


def ingest_fred(retrieved_at: str) -> list[str]:
    ids = []
    for spec in FRED:
        url = FRED_CSV + spec["id"]
        print(f"FRED {spec['id']}")
        rows = read_fred(fetch(url), spec["id"])
        if len(rows) < 10:
            raise SystemExit(f"{spec['id']} returned {len(rows)} rows")
        payload = base_payload(
            {
                **spec,
                "source": "FRED",
                "source_key": spec["id"],
                "source_url": f"https://fred.stlouisfed.org/series/{spec['id']}",
                "download_url": url,
                "release_date": "",
                "next_release": "",
            },
            rows,
            retrieved_at,
        )
        write_series(payload)
        ids.append(spec["id"])
    return ids


def norm_header(name: str) -> str:
    return name.strip().lower().replace("__", "_")


CFTC_FIELDS = {
    "open_interest": "open_interest_all",
    "prod_long": "prod_merc_positions_long_all",
    "prod_short": "prod_merc_positions_short_all",
    "swap_long": "swap_positions_long_all",
    "swap_short": "swap_positions_short_all",
    "swap_spread": "swap_positions_spread_all",
    "mm_long": "m_money_positions_long_all",
    "mm_short": "m_money_positions_short_all",
    "mm_spread": "m_money_positions_spread_all",
    "other_long": "other_rept_positions_long_all",
    "other_short": "other_rept_positions_short_all",
    "nonrept_long": "nonrept_positions_long_all",
    "nonrept_short": "nonrept_positions_short_all",
}


def header_index(normalized: list[str], needle: str, prefix: str = "") -> int:
    if needle in normalized:
        return normalized.index(needle)
    if prefix:
        for index, name in enumerate(normalized):
            if name.startswith(prefix):
                return index
    raise SystemExit(f"CFTC header missing {needle}: {normalized[:12]}")


def header_map(header: list[str]) -> dict[str, int]:
    normalized = [norm_header(item) for item in header]
    found = {
        "name": header_index(normalized, "market_and_exchange_names"),
        "date": header_index(normalized, "report_date_as_yyyy-mm-dd", "report_date"),
        "code": header_index(normalized, "cftc_contract_market_code"),
    }
    for key, needle in CFTC_FIELDS.items():
        found[key] = header_index(normalized, needle)
    return found


def iso_date(raw: str) -> str:
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"bad CFTC date {raw}")


def rows_from_cftc_text(text: str, column_map: dict[str, int] | None) -> tuple[dict[str, int], list[dict]]:
    reader = csv.reader(io.StringIO(text))
    parsed = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not parsed:
        raise SystemExit("empty CFTC file")
    first = parsed[0]
    if norm_header(first[0]) == "market_and_exchange_names":
        column_map = header_map(first)
        body = parsed[1:]
    else:
        if column_map is None:
            raise SystemExit("headerless CFTC file before a headed file was read")
        body = parsed
    hits = []
    for row in body:
        if len(row) <= max(column_map.values()):
            continue
        code = row[column_map["code"]].strip()
        if code not in CFTC_CODES:
            continue
        record = {
            "code": code,
            "name": row[column_map["name"]].strip().strip('"'),
            "date": iso_date(row[column_map["date"]]),
        }
        for key in CFTC_FIELDS:
            raw = row[column_map[key]].strip().replace(",", "")
            if raw == "":
                record = None
                break
            record[key] = canon_number(float(raw))
        if record is None:
            continue
        long_v = float(record["mm_long"])
        short_v = float(record["mm_short"])
        oi = float(record["open_interest"])
        if oi <= 0:
            continue
        record["mm_net"] = canon_number(long_v - short_v)
        record["mm_net_oi"] = f"{(long_v - short_v) / oi:.6f}"
        hits.append(record)
    return column_map, hits


def cftc_field_defs() -> list[dict]:
    labels = {
        "open_interest": ("Open interest", "contracts", False),
        "prod_long": ("Producer long", "contracts", False),
        "prod_short": ("Producer short", "contracts", False),
        "swap_long": ("Swap dealer long", "contracts", False),
        "swap_short": ("Swap dealer short", "contracts", False),
        "swap_spread": ("Swap dealer spread", "contracts", False),
        "mm_long": ("Managed money long", "contracts", False),
        "mm_short": ("Managed money short", "contracts", False),
        "mm_spread": ("Managed money spread", "contracts", False),
        "mm_net": ("Managed money net (long minus short)", "contracts", True),
        "mm_net_oi": ("Managed money net divided by open interest", "share of open interest", True),
        "other_long": ("Other reportable long", "contracts", False),
        "other_short": ("Other reportable short", "contracts", False),
        "nonrept_long": ("Nonreportable long", "contracts", False),
        "nonrept_short": ("Nonreportable short", "contracts", False),
    }
    return [
        {"key": key, "name": name, "unit": unit, "derived": derived}
        for key, (name, unit, derived) in labels.items()
    ]


def ingest_cftc(retrieved_at: str) -> list[str]:
    column_map = None
    collected: dict[str, dict[str, dict]] = {code: {} for code in CFTC_CODES}
    names: dict[str, set[str]] = {code: set() for code in CFTC_CODES}
    gaps = []
    for year in CFTC_YEARS:
        url = CFTC_ZIP.format(year=year)
        print(f"CFTC {year}")
        try:
            blob = fetch(url)
        except Exception as error:  # noqa: BLE001
            gaps.append({"year": year, "error": str(error)})
            print(f"  miss {year}: {error}")
            continue
        archive = zipfile.ZipFile(io.BytesIO(blob))
        texts = [name for name in archive.namelist() if name.lower().endswith((".txt", ".csv"))]
        if not texts:
            gaps.append({"year": year, "error": "no text member"})
            continue
        text = archive.read(texts[0]).decode("latin-1")
        column_map, hits = rows_from_cftc_text(text, column_map)
        for hit in hits:
            collected[hit["code"]][hit["date"]] = hit
            names[hit["code"]].add(hit["name"])
    print("CFTC current")
    current = fetch(CFTC_CURRENT).decode("latin-1")
    column_map, hits = rows_from_cftc_text(current, column_map)
    for hit in hits:
        collected[hit["code"]][hit["date"]] = hit
        names[hit["code"]].add(hit["name"])

    ids = []
    for code, meta in CFTC_CODES.items():
        rows = [collected[code][day] for day in sorted(collected[code])]
        if len(rows) < 200:
            raise SystemExit(f"{meta['id']} has {len(rows)} rows")
        observations = []
        for row in rows:
            item = {"date": row["date"]}
            for field in cftc_field_defs():
                item[field["key"]] = row[field["key"]]
            observations.append(item)
        payload = {
            "id": meta["id"],
            "name": meta["name"],
            "unit": "contracts",
            "frequency": "weekly",
            "group": "positioning",
            "source": "CFTC",
            "source_key": code,
            "source_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
            "download_url": CFTC_CURRENT,
            "history_url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",
            "license": "US government public domain",
            "retrieved_at": retrieved_at,
            "release_date": observations[-1]["date"],
            "next_release": "",
            "derived": False,
            "method": "Filtered disaggregated futures-only report by CFTC contract market code. Managed money net is long minus short and does not include spreads.",
            "inputs": [],
            "market_names": sorted(names[code]),
            "fields": cftc_field_defs(),
            "observations": observations,
            "history_gaps": gaps,
        }
        write_series(payload)
        ids.append(meta["id"])
    return ids


def load(series_id: str) -> dict:
    return json.loads((SERIES_DIR / f"{series_id}.json").read_text())


def value_map(series_id: str) -> dict[str, str]:
    series = load(series_id)
    return {row["date"]: row["value"] for row in series["observations"]}


def align_diff(left_id: str, right_id: str, out_id: str, name: str, unit: str, method: str, group: str, retrieved_at: str) -> None:
    left = value_map(left_id)
    right = value_map(right_id)
    rows = []
    for day in sorted(set(left) & set(right)):
        rows.append({"date": day, "value": canon_number(float(left[day]) - float(right[day]))})
    left_series = load(left_id)
    payload = {
        "id": out_id,
        "name": name,
        "unit": unit,
        "frequency": "daily",
        "group": group,
        "source": "Derived",
        "source_key": out_id,
        "source_url": "",
        "download_url": "",
        "license": "Calculated from US government series stored in this archive",
        "retrieved_at": retrieved_at,
        "release_date": left_series.get("release_date", ""),
        "next_release": "",
        "derived": True,
        "method": method,
        "inputs": [left_id, right_id],
        "fields": [{"key": "value", "name": name, "unit": unit, "derived": True}],
        "observations": rows,
    }
    write_series(payload)


def align_crack(retrieved_at: str) -> None:
    rbob = value_map("RBOB_F1")
    heat = value_map("HO_F1")
    crude = value_map("RCLC1")
    rows = []
    for day in sorted(set(rbob) & set(heat) & set(crude)):
        crack = ((2 * float(rbob[day]) + float(heat[day])) / 3) * 42 - float(crude[day])
        rows.append({"date": day, "value": canon_number(crack)})
    payload = {
        "id": "CRACK_321",
        "name": "3-2-1 crack: ((2 * RBOB_F1 + HO_F1) / 3) * 42 - RCLC1",
        "unit": "dollars per barrel",
        "frequency": "daily",
        "group": "crack",
        "source": "Derived",
        "source_key": "CRACK_321",
        "source_url": "",
        "download_url": "",
        "license": "Calculated from US government series stored in this archive",
        "retrieved_at": retrieved_at,
        "release_date": load("RCLC1").get("release_date", ""),
        "next_release": "",
        "derived": True,
        "method": "RBOB and heating oil futures are dollars per gallon. Times 42 converts the average gallon quote to a barrel quote, then subtracts NYMEX crude contract 1. Dates missing any input are omitted.",
        "inputs": ["RBOB_F1", "HO_F1", "RCLC1"],
        "fields": [
            {
                "key": "value",
                "name": "3-2-1 crack",
                "unit": "dollars per barrel",
                "derived": True,
            }
        ],
        "observations": rows,
    }
    write_series(payload)


def write_catalog(ids: list[str], retrieved_at: str) -> None:
    entries = []
    for series_id in ids:
        series = load(series_id)
        last = series["observations"][-1]
        first = series["observations"][0]
        value_key = "value" if "value" in last else "mm_net"
        entries.append(
            {
                "id": series["id"],
                "name": series["name"],
                "unit": series["unit"],
                "frequency": series["frequency"],
                "group": series["group"],
                "source": series["source"],
                "source_key": series["source_key"],
                "source_url": series["source_url"],
                "download_url": series["download_url"],
                "license": series["license"],
                "retrieved_at": series["retrieved_at"],
                "release_date": series.get("release_date", ""),
                "derived": series["derived"],
                "method": series.get("method", ""),
                "inputs": series.get("inputs", []),
                "fields": series["fields"],
                "count": len(series["observations"]),
                "start": first["date"],
                "end": last["date"],
                "last_value": last.get(value_key, ""),
                "last_field": value_key,
            }
        )
    catalog = {"retrieved_at": retrieved_at, "series": entries}
    (ROOT / "data" / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    manifest = {
        "retrieved_at": retrieved_at,
        "series": [
            {
                "id": item["id"],
                "count": item["count"],
                "start": item["start"],
                "end": item["end"],
                "last_value": item["last_value"],
                "last_field": item["last_field"],
                "source": item["source"],
                "derived": item["derived"],
            }
            for item in entries
        ],
    }
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ids = []
    ids.extend(ingest_eia(retrieved_at))
    ids.extend(ingest_fred(retrieved_at))
    ids.extend(ingest_cftc(retrieved_at))
    align_diff(
        "RCLC1",
        "RCLC4",
        "CL1_MINUS_CL4",
        "NYMEX crude contract 1 minus contract 4",
        "dollars per barrel",
        "RCLC1 minus RCLC4 on dates both contracts print. Positive means the front is above the fourth.",
        "curve",
        retrieved_at,
    )
    align_diff(
        "DGS10",
        "DGS2",
        "DGS10_MINUS_DGS2",
        "10-year Treasury yield minus 2-year Treasury yield",
        "percentage points",
        "DGS10 minus DGS2 on dates both yields print.",
        "macro",
        retrieved_at,
    )
    align_crack(retrieved_at)
    ids.extend(["CL1_MINUS_CL4", "DGS10_MINUS_DGS2", "CRACK_321"])
    write_catalog(ids, retrieved_at)
    print(f"wrote {len(ids)} series")


if __name__ == "__main__":
    main()
