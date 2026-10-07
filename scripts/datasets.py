#!/usr/bin/env python3
"""Write CSV and Parquet downloads for the sheet books and the catalog."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "downloads"


def write_book(book: dict) -> None:
    columns = book["columns"]
    headers = [column["key"] for column in columns]
    csv_path = OUT / f"{book['id']}.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(book["rows"])
    arrays = []
    names = []
    for index, column in enumerate(columns):
        values = [row[index] for row in book["rows"]]
        names.append(column["key"])
        if column["key"] == "date":
            arrays.append(pa.array(values, type=pa.string()))
            continue
        numbers = []
        for value in values:
            numbers.append(None if value == "" else float(value))
        arrays.append(pa.array(numbers, type=pa.float64()))
    table = pa.table(dict(zip(names, arrays)))
    pq.write_table(table, OUT / f"{book['id']}.parquet")
    print(f"{book['id']}: {table.num_rows} rows")


def write_catalog() -> None:
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
    path = OUT / "catalog.csv"
    fields = ["id", "name", "unit", "frequency", "source", "source_url", "derived", "count", "start", "end", "last_value", "retrieved_at", "method"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in catalog["series"]:
            writer.writerow({key: item.get(key, "") for key in fields})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / "data" / "books").glob("*.json"):
        if path.name == "index.json":
            continue
        write_book(json.loads(path.read_text()))
    write_catalog()


if __name__ == "__main__":
    main()
