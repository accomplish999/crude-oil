#!/usr/bin/env python3
"""Committed sheet, downloads, and notebooks have to match the series files."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logic import HOLDOUT_START, adjacent_log_returns, canon_number, mad_scale, pairs  # noqa: E402


class PublishTests(unittest.TestCase):
    def test_catalog_matches_series_files(self) -> None:
        catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
        self.assertGreaterEqual(len(catalog["series"]), 40)
        for item in catalog["series"]:
            series = json.loads((ROOT / "data" / "series" / f"{item['id']}.json").read_text())
            last = series["observations"][-1]
            field = item["last_field"]
            self.assertEqual(last["date"], item["end"], item["id"])
            self.assertEqual(last[field], item["last_value"], item["id"])
            self.assertEqual(series["retrieved_at"], item["retrieved_at"])
            if item["derived"]:
                self.assertTrue(item["method"])

    def test_price_book_matches_rwtc_and_z(self) -> None:
        book = json.loads((ROOT / "data" / "books" / "prices.json").read_text())
        keys = [column["key"] for column in book["columns"]]
        value_index = keys.index("RWTC")
        z_index = value_index
        series = json.loads((ROOT / "data" / "series" / "RWTC.json").read_text())
        last = series["observations"][-1]
        book_last = next(row for row in reversed(book["rows"]) if row[value_index])
        self.assertEqual(book_last[0], last["date"])
        self.assertEqual(book_last[value_index], last["value"])
        rets = adjacent_log_returns(pairs(series))
        train = [item["log_return"] for item in rets if item["date"] < HOLDOUT_START]
        center, scale = mad_scale(train)
        expected = {
            item["date"].isoformat(): canon_number((item["log_return"] - center) / scale)
            for item in rets
        }
        checked = 0
        for row, zrow in zip(book["rows"], book["z"]):
            if row[0] < "2024-01-01" or not row[value_index]:
                continue
            self.assertEqual(zrow[z_index], expected[row[0]])
            checked += 1
            if checked == 20:
                break
        self.assertEqual(checked, 20)

    def test_parquet_matches_csv_width(self) -> None:
        table = pq.read_table(ROOT / "public" / "downloads" / "prices.parquet")
        book = json.loads((ROOT / "data" / "books" / "prices.json").read_text())
        self.assertEqual(table.num_rows, len(book["rows"]))
        self.assertEqual(table.column_names[0], "date")

    def test_notebooks_match_studies(self) -> None:
        studies = json.loads((ROOT / "data" / "studies.json").read_text())
        self.assertGreaterEqual(len(studies["studies"]), 20)
        for study in studies["studies"]:
            path = ROOT / "notebooks" / f"{study['index']}-{study['slug']}.ipynb"
            public = ROOT / "public" / "notebooks" / path.name
            self.assertTrue(path.exists(), path.name)
            notebook = json.loads(path.read_text())
            self.assertEqual(notebook["nbformat"], 4)
            blob = json.dumps(notebook)
            self.assertIn(study["verdict_line"], blob)
            self.assertEqual(path.read_text(), public.read_text())

    def test_timesfm_matches_the_seasonal_holdout(self) -> None:
        payload = json.loads((ROOT / "data" / "timesfm.json").read_text())
        studies = json.loads((ROOT / "data" / "studies.json").read_text())
        forecast = next(study for study in studies["studies"] if study["slug"] == "forecast")
        self.assertEqual(payload["model"], "google/timesfm-3.0-pytorch")
        self.assertEqual(payload["n"], forecast["stats"]["n"])
        self.assertAlmostEqual(payload["seasonal_mae"], forecast["stats"]["seasonal_mae"])
        self.assertAlmostEqual(payload["flat_mae"], forecast["stats"]["flat_mae"])
        self.assertAlmostEqual(payload["timesfm_mae"], forecast["stats"]["timesfm_mae"])
        self.assertEqual(len(payload["months"]), payload["n"])
        self.assertIn(payload["summary"], json.dumps(forecast))
        self.assertNotIn("\u2014", payload["summary"])

    def test_changelog_has_a_baseline(self) -> None:
        log = json.loads((ROOT / "data" / "changelog.json").read_text())
        self.assertGreaterEqual(len(log["entries"]), 1)
        self.assertIn("snapshot", log["entries"][-1])
        self.assertTrue((ROOT / "CHANGELOG.md").exists())


if __name__ == "__main__":
    unittest.main()
