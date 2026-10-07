#!/usr/bin/env python3
"""Derived metrics. Formulas and bars are fixed in this file.

Train moments used as rules come from dates before 2020-01-01.
A missing input drops the date. Nothing is interpolated.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logic import (  # noqa: E402
    HOLDOUT_START,
    adjacent_log_returns,
    canon_number,
    fmt_num,
    fmt_pct,
    is_holdout,
    mad_scale,
    mean,
    median,
    nearest_rank,
    pairs,
    pearson,
    release_return,
    sign,
    weekly_changes,
)

SERIES = ROOT / "data" / "series"


def load(series_id: str) -> dict:
    return json.loads((SERIES / f"{series_id}.json").read_text())


def snapshot_time() -> str:
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
    return catalog["retrieved_at"]


def split(items, key):
    train, hold = [], []
    for item in items:
        (hold if is_holdout(key(item)) else train).append(item)
    return train, hold


def sign_verdict(train_gap, hold_gap, lead: str) -> tuple[str, str]:
    train_sign, hold_sign = sign(train_gap), sign(hold_gap)
    if train_sign == 0 or hold_sign == 0:
        return "flat", f"{lead} One window is flat, so there is no sign to carry."
    if train_sign == hold_sign:
        return "held", f"{lead} The holdout kept the train sign."
    return "failed", f"{lead} The holdout flipped the train sign."


def negative_corr(train_corr, hold_corr, lead: str) -> tuple[str, str]:
    if hold_corr is None:
        return "flat", f"{lead} The holdout correlation is undefined."
    if hold_corr < 0:
        tail = "The holdout correlation is negative, which was the bar."
        if train_corr is not None and train_corr >= 0:
            tail += " The train correlation was not negative."
        return "held", f"{lead} {tail}"
    return "failed", f"{lead} The holdout correlation is not negative. The bar was missed."


def positive_diff(diff, lead: str) -> tuple[str, str]:
    if diff is None:
        return "flat", f"{lead} The holdout gap is undefined."
    if diff > 0:
        return "held", f"{lead} The holdout gap is positive, which was the bar."
    return "failed", f"{lead} The holdout gap is not positive. The bar was missed."


def price_index(rows: list[tuple[date, float]]) -> dict[date, int]:
    return {day: index for index, (day, _) in enumerate(rows)}


def index_on_or_after(rows: list[tuple[date, float]], day: date, limit: int = 3) -> int | None:
    for index, (stamp, _) in enumerate(rows):
        if stamp < day:
            continue
        if (stamp - day).days <= limit:
            return index
        return None
    return None


def forward_at(rows: list[tuple[date, float]], index: int, steps: int = 5) -> float | None:
    target = index + steps
    if target >= len(rows):
        return None
    start = rows[index][1]
    end = rows[target][1]
    if start <= 0 or end <= 0:
        return None
    return math.log(end / start)


def write_series(
    series_id: str,
    name: str,
    unit: str,
    frequency: str,
    method: str,
    inputs: list[str],
    observations: list[tuple[date, float]],
    retrieved_at: str,
) -> dict:
    rows = [{"date": day.isoformat(), "value": canon_number(value)} for day, value in observations]
    if not rows:
        raise RuntimeError(f"{series_id} produced no rows")
    payload = {
        "id": series_id,
        "name": name,
        "unit": unit,
        "frequency": frequency,
        "group": "metric",
        "source": "Derived",
        "source_key": series_id,
        "source_url": "",
        "download_url": "",
        "license": "Calculated from US government series stored in this archive",
        "retrieved_at": retrieved_at,
        "release_date": "",
        "next_release": "",
        "derived": True,
        "method": method,
        "inputs": inputs,
        "fields": [{"key": "value", "name": name, "unit": unit, "derived": True}],
        "observations": rows,
    }
    (SERIES / f"{series_id}.json").write_text(json.dumps(payload, indent=2) + "\n")
    last = rows[-1]
    return {
        "id": series_id,
        "name": name,
        "unit": unit,
        "frequency": frequency,
        "group": "metric",
        "source": "Derived",
        "source_key": series_id,
        "source_url": "",
        "download_url": "",
        "license": payload["license"],
        "retrieved_at": retrieved_at,
        "release_date": "",
        "derived": True,
        "method": method,
        "inputs": inputs,
        "fields": payload["fields"],
        "count": len(rows),
        "start": rows[0]["date"],
        "end": last["date"],
        "last_value": last["value"],
        "last_field": "value",
    }


def upsert_catalog(entries: list[dict]) -> None:
    path = ROOT / "data" / "catalog.json"
    catalog = json.loads(path.read_text())
    order = [item["id"] for item in catalog["series"]]
    by_id = {item["id"]: item for item in catalog["series"]}
    for entry in entries:
        if entry["id"] not in by_id:
            order.append(entry["id"])
        by_id[entry["id"]] = entry
    catalog["series"] = [by_id[series_id] for series_id in order]
    path.write_text(json.dumps(catalog, indent=2) + "\n")
    manifest = {
        "retrieved_at": catalog["retrieved_at"],
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
            for item in catalog["series"]
        ],
    }
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def bars(stat: str, label: str, categories: list[str], values: list[float | None]) -> dict:
    return {
        "type": "bars",
        "stat": stat,
        "stat_label": label,
        "categories": categories,
        "series": [{"name": label, "values": [value or 0 for value in values]}],
    }


def study(
    slug: str,
    index: str,
    title: str,
    kicker: str,
    question: str,
    formula: str,
    status: str,
    line: str,
    chart: dict,
    table: dict,
    method: list[str],
    stats: dict,
) -> dict:
    return {
        "slug": slug,
        "index": index,
        "title": title,
        "kicker": kicker,
        "question": question,
        "verdict": status,
        "verdict_line": line,
        "group": "metric",
        "formula": formula,
        "chart": chart,
        "table": table,
        "cells": [
            {"label": "Question", "body": [question, formula]},
            {"label": "Method", "body": method},
            {"label": "Result", "body": [line]},
        ],
        "stats": stats,
    }


def card(entry: dict, formula: str, question: str, status: str, line: str, constants: dict) -> dict:
    return {
        "id": entry["id"],
        "name": entry["name"],
        "formula": formula,
        "unit": entry["unit"],
        "inputs": entry["inputs"],
        "latest_date": entry["end"],
        "latest_value": entry["last_value"],
        "question": question,
        "verdict": status,
        "verdict_line": line,
        "constants": {key: value for key, value in constants.items() if isinstance(value, (int, float, str)) or value is None},
        "study_slug": entry["id"].lower().replace("_", "-"),
    }


def surprise_and_cover(prices, retrieved_at):
    stocks = weekly_changes(pairs(load("WCESTUS1")))
    usable = []
    observations = []
    skipped = 0
    for change in stocks:
        window = [item["change"] for item in stocks if item["date"] < change["date"]][-52:]
        if len(window) < 52:
            continue
        baseline = mean(window)
        if baseline is None:
            continue
        surprise = change["change"] - baseline
        observations.append((change["date"], surprise))
        reaction = release_return(prices, change["date"])
        if reaction is None:
            skipped += 1
            continue
        usable.append({"date": change["date"], "surprise": surprise, "log_return": reaction["log_return"]})
    formula = (
        "Weekly change in EIA WCESTUS1, kept only when the week-ending dates are 7 days apart, "
        "minus the mean of the prior 52 kept changes. The mean uses weeks strictly before the current week. "
        "This is a trailing baseline, not an analyst survey."
    )
    train, hold = split(usable, lambda item: item["date"])

    def corr(items):
        return pearson([item["surprise"] for item in items], [item["log_return"] for item in items])

    tr, ho = corr(train), corr(hold)
    lead = (
        f"Train correlation of the mean-baseline surprise with the release-day RWTC log return is {fmt_num(tr)}. "
        f"Holdout correlation is {fmt_num(ho)}."
    )
    status, line = negative_corr(tr, ho, lead)
    question = (
        "Is the holdout correlation between this mean-baseline stock surprise and the nominal EIA Wednesday RWTC return negative?"
    )
    entry = write_series(
        "INV_SURPRISE",
        "Commercial crude surprise versus the prior 52-week mean change",
        "thousand barrels",
        "weekly",
        formula,
        ["WCESTUS1"],
        observations,
        retrieved_at,
    )
    packed = study(
        "inv-surprise",
        "11",
        "Inventory surprise proxy",
        "Mean of the prior 52 weeks",
        question,
        formula,
        status,
        line,
        bars(fmt_num(ho), "correlation", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "WCESTUS1 change minus the prior 52-week mean, versus the Wednesday RWTC log return",
            "columns": ["Window", "n", "Correlation"],
            "rows": [
                ["Train", str(len(train)), fmt_num(tr)],
                ["Holdout", str(len(hold)), fmt_num(ho)],
                ["Skipped, no Wednesday RWTC print", str(skipped), ""],
            ],
        },
        [
            "The EIA week ends Friday. The nominal release is the Wednesday five days later. If that Wednesday has no RWTC print, the week is skipped. A Thursday holiday release is not moved.",
            "The bar is a negative holdout correlation. The threshold is not refit after the holdout is seen.",
        ],
        {"train_correlation": tr, "holdout_correlation": ho, "n_train": len(train), "n_holdout": len(hold)},
    )
    return entry, packed, card(entry, formula, question, status, line, {"train_correlation": tr, "holdout_correlation": ho})


def cushing_cover(prices, retrieved_at):
    cushing = pairs(load("CUSHING"))
    runs = {day: value for day, value in pairs(load("WCRRIUS2"))}
    observations = []
    usable = []
    by_date = price_index(prices)
    for day, stocks in cushing:
        throughput = runs.get(day)
        if throughput is None or throughput <= 0:
            continue
        cover = stocks / throughput
        observations.append((day, cover))
        index = by_date.get(day)
        if index is None:
            index = index_on_or_after(prices, day, 3)
        if index is None:
            continue
        forward = forward_at(prices, index, 5)
        if forward is None:
            continue
        usable.append({"date": day, "cover": cover, "forward": forward})
    train, hold = split(usable, lambda item: item["date"])
    threshold = nearest_rank([item["cover"] for item in train], 0.20)

    def gap(items):
        low = [item["forward"] for item in items if item["cover"] < threshold]
        rest = [item["forward"] for item in items if item["cover"] >= threshold]
        left, right = mean(low), mean(rest)
        if left is None or right is None:
            return None, len(low), len(rest)
        return left - right, len(low), len(rest)

    tr, tr_n, tr_r = gap(train)
    ho, ho_n, ho_r = gap(hold)
    formula = (
        "Cushing crude stocks (thousand barrels) divided by US refiner net inputs of crude "
        "(thousand barrels per day) on the same Friday. The result is days. "
        f"Low cover is a print below the train 20th percentile, frozen at {fmt_num(threshold, 3)} days."
    )
    lead = (
        f"Train 20th percentile of days of cover is {fmt_num(threshold, 3)}. "
        f"Train gap, low cover minus the rest, is {fmt_pct(tr)} ({tr_n} low, {tr_r} rest). "
        f"Holdout gap is {fmt_pct(ho)} ({ho_n} low, {ho_r} rest)."
    )
    status, line = sign_verdict(tr, ho, lead)
    question = (
        "Does the gap between five-print RWTC returns when Cushing days of cover are below the pre-2020 20th percentile, "
        "and when they are not, keep its sign after 2019?"
    )
    entry = write_series(
        "CUSHING_COVER",
        "Cushing days of cover",
        "days",
        "weekly",
        formula,
        ["CUSHING", "WCRRIUS2"],
        observations,
        retrieved_at,
    )
    packed = study(
        "cushing-cover",
        "12",
        "Cushing days of cover",
        "Stocks over refinery crude inputs",
        question,
        formula,
        status,
        line,
        bars(fmt_pct(ho), "low cover minus the rest", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "Five-print RWTC log return when days of cover are below the frozen train 20th percentile",
            "columns": ["Window", "Low n", "Rest n", "Low minus rest"],
            "rows": [
                ["Train", str(tr_n), str(tr_r), fmt_pct(tr)],
                ["Holdout", str(ho_n), str(ho_r), fmt_pct(ho)],
            ],
        },
        [
            "The price date is the Friday print when RWTC exists that day, otherwise the next RWTC print within 3 calendar days. The return then steps five published RWTC prints.",
            "The percentile is nearest-rank on the train window only.",
        ],
        {"threshold": threshold, "train_gap": tr, "holdout_gap": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {"threshold_days": threshold, "train_gap": tr, "holdout_gap": ho})


def curve_z(prices, retrieved_at):
    spread = pairs(load("CL1_MINUS_CL4"))
    train_levels = [value for day, value in spread if day < HOLDOUT_START]
    center = mean(train_levels)
    scale = statistics.pstdev(train_levels) if len(train_levels) > 1 else None
    observations = []
    usable = []
    by_date = price_index(prices)
    for day, value in spread:
        if center is None or scale is None or scale == 0:
            continue
        zed = (value - center) / scale
        observations.append((day, zed))
        index = by_date.get(day)
        if index is None:
            continue
        forward = forward_at(prices, index, 5)
        if forward is None:
            continue
        usable.append({"date": day, "z": zed, "forward": forward})
    train, hold = split(usable, lambda item: item["date"])

    def gap(items):
        high = [item["forward"] for item in items if item["z"] > 1]
        low = [item["forward"] for item in items if item["z"] < -1]
        left, right = mean(high), mean(low)
        if left is None or right is None:
            return None, len(high), len(low)
        return left - right, len(high), len(low)

    tr, tr_h, tr_l = gap(train)
    ho, ho_h, ho_l = gap(hold)
    formula = (
        "(CL1_MINUS_CL4 minus the train mean) divided by the train population standard deviation. "
        f"Train mean {fmt_num(center, 3)} dollars per barrel. Train standard deviation {fmt_num(scale, 3)}. "
        "Both moments stop at 31 Dec 2019 and are applied to every later print. "
        "A positive CL1_MINUS_CL4 means the front NYMEX contract is above the fourth."
    )
    lead = (
        f"Train gap, z above 1 minus z below -1, is {fmt_pct(tr)} ({tr_h} high, {tr_l} low). "
        f"Holdout gap is {fmt_pct(ho)} ({ho_h} high, {ho_l} low)."
    )
    status, line = sign_verdict(tr, ho, lead)
    question = (
        "Does the gap between five-print RWTC returns when the curve z-score is above 1 and when it is below -1 keep its sign after 2019?"
    )
    entry = write_series(
        "CURVE_Z",
        "Curve z-score, contract 1 minus contract 4",
        "z-score",
        "daily",
        formula,
        ["CL1_MINUS_CL4"],
        observations,
        retrieved_at,
    )
    packed = study(
        "curve-z",
        "13",
        "Curve regime score",
        "Train mean and standard deviation",
        question,
        formula,
        status,
        line,
        bars(fmt_pct(ho), "z>1 minus z<-1", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "Five-print RWTC return, high curve z versus low curve z",
            "columns": ["Window", "z>1 n", "z<-1 n", "Gap"],
            "rows": [
                ["Train", str(tr_h), str(tr_l), fmt_pct(tr)],
                ["Holdout", str(ho_h), str(ho_l), fmt_pct(ho)],
            ],
        },
        [
            "The score is a level z-score of the stored spread, not a new curve. EIA's contract history in this snapshot ends where RCLC1 ends.",
            "Prints with z between -1 and 1 are in neither bucket.",
        ],
        {"train_mean": center, "train_std": scale, "train_gap": tr, "holdout_gap": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {"train_mean": center, "train_std": scale})


def positioning(prices, retrieved_at):
    rows = []
    for row in load("CFTC_CL")["observations"]:
        if "mm_net_oi" not in row:
            continue
        rows.append((date.fromisoformat(row["date"]), float(row["mm_net_oi"])))
    rows.sort()
    train_levels = [value for day, value in rows if day < HOLDOUT_START]
    center = mean(train_levels)
    scale = statistics.pstdev(train_levels) if len(train_levels) > 1 else None
    ordered = sorted(train_levels)
    observations_z = []
    observations_pct = []
    usable = []
    by_date = price_index(prices)
    for day, value in rows:
        if center is None or not scale:
            continue
        zed = (value - center) / scale
        rank = sum(1 for item in ordered if item <= value) / len(ordered)
        observations_z.append((day, zed))
        observations_pct.append((day, rank * 100))
        index = by_date.get(day)
        if index is None:
            index = index_on_or_after(prices, day, 3)
        if index is None:
            continue
        forward = forward_at(prices, index, 5)
        if forward is None:
            continue
        usable.append({"date": day, "z": zed, "forward": forward})
    train, hold = split(usable, lambda item: item["date"])

    def gap(items):
        hot = [item["forward"] for item in items if item["z"] > 1.5]
        rest = [item["forward"] for item in items if item["z"] <= 1.5]
        left, right = mean(hot), mean(rest)
        if left is None or right is None:
            return None, len(hot), len(rest)
        return left - right, len(hot), len(rest)

    tr, tr_h, tr_r = gap(train)
    ho, ho_h, ho_r = gap(hold)
    formula = (
        "Managed-money net divided by open interest on CFTC 067651. "
        "Z-score uses the train mean and the train population standard deviation of that ratio. "
        f"Train mean {fmt_num(center, 4)}. Train standard deviation {fmt_num(scale, 4)}. "
        "The percentile is the share of train ratios at or below the current print. Spreads are not inside the net."
    )
    lead = (
        f"Train gap, z above 1.5 minus the rest, is {fmt_pct(tr)} ({tr_h} extreme, {tr_r} rest). "
        f"Holdout gap is {fmt_pct(ho)} ({ho_h} extreme, {ho_r} rest)."
    )
    status, line = sign_verdict(tr, ho, lead)
    question = (
        "Does the gap between five-print RWTC returns when the managed-money z-score is above 1.5, and when it is not, keep its sign after 2019?"
    )
    z_entry = write_series(
        "COT_Z",
        "Managed money z-score, WTI-PHYSICAL",
        "z-score",
        "weekly",
        formula,
        ["CFTC_CL"],
        observations_z,
        retrieved_at,
    )
    pct_entry = write_series(
        "COT_PCT",
        "Managed money percentile versus the pre-2020 distribution",
        "percentile",
        "weekly",
        "Share of train mm_net_oi prints at or below the current print, times 100. The train distribution is frozen.",
        ["CFTC_CL"],
        observations_pct,
        retrieved_at,
    )
    packed = study(
        "cot-z",
        "14",
        "Positioning z-score",
        "Managed money net over open interest",
        question,
        formula,
        status,
        line,
        bars(fmt_pct(ho), "z>1.5 minus the rest", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "Five-print RWTC return when COT_Z is above 1.5",
            "columns": ["Window", "Extreme n", "Rest n", "Gap"],
            "rows": [
                ["Train", str(tr_h), str(tr_r), fmt_pct(tr)],
                ["Holdout", str(ho_h), str(ho_r), fmt_pct(ho)],
            ],
        },
        [
            "The report date is joined to RWTC on that date, or to the next print within 3 calendar days.",
            "COT_PCT is the frozen train percentile of the same ratio. The scored test uses the z-score, not a second cutoff chosen later.",
        ],
        {"train_mean": center, "train_std": scale, "train_gap": tr, "holdout_gap": ho},
    )
    return (
        [z_entry, pct_entry],
        packed,
        card(z_entry, formula, question, status, line, {"train_mean": center, "train_std": scale, "percentile_latest": pct_entry["last_value"]}),
    )


def crack_gap(prices, retrieved_at):
    crack = pairs(load("CRACK_321"))
    train_levels = [value for day, value in crack if day < HOLDOUT_START]
    center = median(train_levels)
    observations = [(day, value - center) for day, value in crack]
    usable = []
    by_date = price_index(prices)
    for day, value in observations:
        index = by_date.get(day)
        if index is None:
            continue
        forward = forward_at(prices, index, 5)
        if forward is None:
            continue
        usable.append({"date": day, "gap": value, "forward": forward})
    train, hold = split(usable, lambda item: item["date"])

    def corr(items):
        return pearson([item["gap"] for item in items], [item["forward"] for item in items])

    tr, ho = corr(train), corr(hold)
    formula = (
        "CRACK_321 minus its train median. "
        f"Train median {fmt_num(center, 3)} dollars per barrel. "
        "CRACK_321 is ((2 * RBOB_F1 + HO_F1) / 3) * 42 minus RCLC1. "
        "A date is absent when any input is absent. The futures workbooks end before the spot series."
    )
    lead = f"Train correlation of the crack gap with the next five-print RWTC return is {fmt_num(tr)}. Holdout correlation is {fmt_num(ho)}."
    status, line = sign_verdict(tr, ho, lead)
    question = (
        "Does the correlation between the crack's distance from its pre-2020 median and the next five-print RWTC return keep its sign after 2019?"
    )
    entry = write_series(
        "CRACK_GAP",
        "3-2-1 crack minus the pre-2020 median",
        "dollars per barrel",
        "daily",
        formula,
        ["CRACK_321"],
        observations,
        retrieved_at,
    )
    packed = study(
        "crack-gap",
        "15",
        "Crack gap",
        "Distance from the train median",
        question,
        formula,
        status,
        line,
        bars(fmt_num(ho), "correlation", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "Crack minus the frozen train median, versus the next five RWTC prints",
            "columns": ["Window", "n", "Correlation"],
            "rows": [["Train", str(len(train)), fmt_num(tr)], ["Holdout", str(len(hold)), fmt_num(ho)]],
        },
        ["The bar is sign agreement of the correlation. A rich crack is not given a second rule after the result is in."],
        {"train_median": center, "train_correlation": tr, "holdout_correlation": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {"train_median": center})


def realized_vol(prices, retrieved_at):
    rets = adjacent_log_returns(prices)
    observations = []
    usable = []
    by_date = price_index(prices)
    for index, item in enumerate(rets):
        window = rets[index - 19 : index + 1] if index >= 19 else []
        if len(window) < 20:
            continue
        vol = statistics.pstdev([row["log_return"] for row in window]) * math.sqrt(252)
        observations.append((item["date"], vol))
    train_vols = [value for day, value in observations if day < HOLDOUT_START]
    threshold = nearest_rank(train_vols, 0.80)
    for day, vol in observations:
        index = by_date.get(day)
        if index is None:
            continue
        forward = forward_at(prices, index, 5)
        if forward is None:
            continue
        usable.append({"date": day, "vol": vol, "forward": abs(forward), "high": vol >= threshold})
    train, hold = split(usable, lambda item: item["date"])

    def gap(items):
        high = [item["forward"] for item in items if item["high"]]
        rest = [item["forward"] for item in items if not item["high"]]
        left, right = mean(high), mean(rest)
        if left is None or right is None:
            return None, len(high), len(rest)
        return left - right, len(high), len(rest)

    tr, tr_h, tr_r = gap(train)
    ho, ho_h, ho_r = gap(hold)
    formula = (
        "Population standard deviation of the last 20 adjacent RWTC log returns, times the square root of 252. "
        "A return enters only when the two prints are 1 to 5 calendar days apart. "
        f"High realized vol is at or above the train 80th percentile, frozen at {fmt_num(threshold, 4)}. "
        "Implied volatility is not in this archive. No implied-versus-realized ratio is computed."
    )
    lead = (
        f"Train gap in mean absolute five-print return, high vol minus the rest, is {fmt_pct(tr)}. "
        f"Holdout gap is {fmt_pct(ho)} ({ho_h} high, {ho_r} rest)."
    )
    status, line = positive_diff(ho, lead)
    question = (
        "When 20-print realized volatility sits at or above its pre-2020 80th percentile, "
        "is the holdout mean absolute five-print RWTC return larger than on the other days?"
    )
    entry = write_series(
        "RV20",
        "20-print realized volatility, RWTC",
        "annualized log-return standard deviation",
        "daily",
        formula,
        ["RWTC"],
        observations,
        retrieved_at,
    )
    packed = study(
        "realized-vol",
        "16",
        "Realized volatility",
        "No implied vol in the free file",
        question,
        formula,
        status,
        line,
        bars(fmt_pct(ho), "high vol minus the rest", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "Mean absolute five-print RWTC return when RV20 is at or above the frozen train 80th percentile",
            "columns": ["Window", "High n", "Rest n", "High minus rest"],
            "rows": [
                ["Train", str(tr_h), str(tr_r), fmt_pct(tr)],
                ["Holdout", str(ho_h), str(ho_r), fmt_pct(ho)],
            ],
        },
        [
            "The bar is a positive holdout gap. The train gap is reported and is not used to move the cutoff.",
            "An options implied volatility would need a free, redistributable options history. This snapshot does not have one.",
        ],
        {"threshold": threshold, "train_gap": tr, "holdout_gap": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {"threshold": threshold})


def eia_profile(prices):
    stocks = weekly_changes(pairs(load("WCESTUS1")))
    usable = []
    for change in stocks:
        window = [item["change"] for item in stocks if item["date"] < change["date"]][-52:]
        if len(window) < 52:
            continue
        baseline = median(window)
        reaction = release_return(prices, change["date"])
        if reaction is None:
            continue
        usable.append({"date": change["date"], "surprise": change["change"] - baseline, "log_return": reaction["log_return"]})
    train, hold = split(usable, lambda item: item["date"])
    surprises = [item["surprise"] for item in train]
    edges = [nearest_rank(surprises, p) for p in (0.25, 0.50, 0.75)]

    def bucket(value: float) -> int:
        if value <= edges[0]:
            return 1
        if value <= edges[1]:
            return 2
        if value <= edges[2]:
            return 3
        return 4

    def means(items):
        grouped = defaultdict(list)
        for item in items:
            grouped[bucket(item["surprise"])].append(item["log_return"])
        return {key: mean(values) for key, values in grouped.items() if mean(values) is not None}

    train_means = means(train)
    hold_means = means(hold)
    shared = [key for key in (1, 2, 3, 4) if key in train_means and key in hold_means]
    if len(shared) < 3:
        corr = None
    else:
        left = [train_means[key] for key in shared]
        right = [hold_means[key] for key in shared]
        corr = pearson(ranks(left), ranks(right))
    formula = (
        "The same weekly WCESTUS1 surprise as the inventory study: change minus the prior 52-week median. "
        "Train quartile edges are frozen. Each week is placed in one of four bins. "
        "The score is the Spearman correlation of the train bin-mean release return with the holdout bin-mean."
    )
    lead = (
        f"Train quartile edges, thousand barrels: {fmt_num(edges[0], 1)}, {fmt_num(edges[1], 1)}, {fmt_num(edges[2], 1)}. "
        f"Spearman correlation of the bin means is {fmt_num(corr)}."
    )
    if corr is None:
        status, line = "flat", f"{lead} Not enough populated bins."
    elif corr > 0:
        status, line = "held", f"{lead} The correlation is above zero, which was the bar."
    else:
        status, line = "failed", f"{lead} The correlation is not above zero. The bar was missed."
    question = "Do the four pre-2020 surprise bins rank the Wednesday RWTC return the same way after 2019?"
    rows = []
    for key in (1, 2, 3, 4):
        rows.append([str(key), fmt_pct(train_means.get(key)), fmt_pct(hold_means.get(key))])
    packed = study(
        "eia-profile",
        "17",
        "EIA-day reaction profile",
        "Four frozen surprise bins",
        question,
        formula,
        status,
        line,
        bars(fmt_num(corr), "Spearman of bin means", ["Q1", "Q2", "Q3", "Q4"], [hold_means.get(key) for key in (1, 2, 3, 4)]),
        {
            "caption": "Mean Wednesday RWTC log return by inventory-surprise quartile",
            "columns": ["Quartile", "Train mean", "Holdout mean"],
            "rows": rows,
        },
        [
            "Quartile 1 is the most negative surprise (a larger draw, or a smaller build, than the prior 52-week median).",
            "Spearman is the Pearson correlation of the ranks of the four means. The bar is a positive correlation. Bins are not reordered after the holdout.",
        ],
        {"correlation": corr, "q25": edges[0], "q50": edges[1], "q75": edges[2]},
    )
    return packed


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    out = [0.0] * len(values)
    for rank, index in enumerate(order, start=1):
        out[index] = float(rank)
    return out


def seasonal_stocks(prices, retrieved_at):
    levels = pairs(load("WCESTUS1"))
    by_month = defaultdict(list)
    for day, value in levels:
        if day < HOLDOUT_START:
            by_month[day.month].append(value)
    month_mean = {month: mean(values) for month, values in by_month.items()}
    observations = []
    usable = []
    for day, value in levels:
        base = month_mean.get(day.month)
        if base is None:
            continue
        deviation = value - base
        observations.append((day, deviation))
        reaction = release_return(prices, day)
        if reaction is None:
            continue
        usable.append({"date": day, "deviation": deviation, "log_return": reaction["log_return"]})
    train, hold = split(usable, lambda item: item["date"])

    def corr(items):
        return pearson([item["deviation"] for item in items], [item["log_return"] for item in items])

    tr, ho = corr(train), corr(hold)
    formula = (
        "WCESTUS1 level minus the train mean level for that calendar month. "
        "Month means are frozen on weeks before 2020. A later January is compared with the pre-2020 January mean, not with a mean that includes itself."
    )
    lead = f"Train correlation of the seasonal deviation with the Wednesday RWTC return is {fmt_num(tr)}. Holdout correlation is {fmt_num(ho)}."
    status, line = sign_verdict(tr, ho, lead)
    question = "Does the correlation between seasonally adjusted commercial crude stocks and the Wednesday RWTC return keep its sign after 2019?"
    entry = write_series(
        "SEAS_STOCK",
        "Commercial crude stocks minus the pre-2020 month mean",
        "thousand barrels",
        "weekly",
        formula,
        ["WCESTUS1"],
        observations,
        retrieved_at,
    )
    packed = study(
        "seas-stock",
        "18",
        "Seasonal stock deviation",
        "Level minus the train month mean",
        question,
        formula,
        status,
        line,
        bars(fmt_num(ho), "correlation", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "WCESTUS1 minus the frozen calendar-month mean, versus the Wednesday RWTC return",
            "columns": ["Window", "n", "Correlation"],
            "rows": [["Train", str(len(train)), fmt_num(tr)], ["Holdout", str(len(hold)), fmt_num(ho)]],
        },
        ["The bar is sign agreement. The popular sign would be negative. The test does not switch to that story after the numbers are in."],
        {"train_correlation": tr, "holdout_correlation": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {})


def utilization(prices, retrieved_at):
    levels = pairs(load("WPULEUS3"))
    train_levels = [value for day, value in levels if day < HOLDOUT_START]
    center = median(train_levels)
    distances = [abs(value - center) for value in train_levels]
    cutoff = nearest_rank(distances, 0.90)
    observations = [(day, value - center) for day, value in levels]
    usable = []
    for day, deviation in observations:
        reaction = release_return(prices, day)
        if reaction is None:
            continue
        usable.append(
            {
                "date": day,
                "deviation": deviation,
                "abs_return": abs(reaction["log_return"]),
                "anomaly": abs(deviation) >= cutoff,
            }
        )
    train, hold = split(usable, lambda item: item["date"])

    def gap(items):
        hot = [item["abs_return"] for item in items if item["anomaly"]]
        rest = [item["abs_return"] for item in items if not item["anomaly"]]
        left, right = mean(hot), mean(rest)
        if left is None or right is None:
            return None, len(hot), len(rest)
        return left - right, len(hot), len(rest)

    tr, tr_h, tr_r = gap(train)
    ho, ho_h, ho_r = gap(hold)
    formula = (
        "WPULEUS3 minus its train median, in percentage points of utilization. "
        f"Train median {fmt_num(center, 2)} percent. "
        f"An anomaly is an absolute deviation at or above the train 90th percentile of absolute deviations, frozen at {fmt_num(cutoff, 2)} points."
    )
    lead = (
        f"Train gap in mean absolute Wednesday return, anomaly minus the rest, is {fmt_pct(tr)}. "
        f"Holdout gap is {fmt_pct(ho)} ({ho_h} anomalies, {ho_r} other weeks)."
    )
    status, line = positive_diff(ho, lead)
    question = (
        "On weeks when refinery utilization is further from its pre-2020 median than the train 90th percentile of that distance, "
        "is the holdout mean absolute Wednesday RWTC return larger?"
    )
    entry = write_series(
        "UTIL_DEV",
        "Refinery utilization minus the pre-2020 median",
        "percentage points",
        "weekly",
        formula,
        ["WPULEUS3"],
        observations,
        retrieved_at,
    )
    packed = study(
        "util-anomaly",
        "19",
        "Refinery utilization",
        "Distance from the train median",
        question,
        formula,
        status,
        line,
        bars(fmt_pct(ho), "anomaly minus the rest", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "Mean absolute Wednesday RWTC return on utilization anomalies",
            "columns": ["Window", "Anomaly n", "Rest n", "Anomaly minus rest"],
            "rows": [
                ["Train", str(tr_h), str(tr_r), fmt_pct(tr)],
                ["Holdout", str(ho_h), str(ho_r), fmt_pct(ho)],
            ],
        },
        ["The bar is a positive holdout gap in absolute return. The cutoff stays at the train 90th percentile."],
        {"center": center, "cutoff": cutoff, "train_gap": tr, "holdout_gap": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {"cutoff": cutoff})


def spr_flow(prices, retrieved_at):
    changes = weekly_changes(pairs(load("WCSSTUS1")))
    observations = [(item["date"], item["change"]) for item in changes]
    usable = []
    skipped = 0
    for item in changes:
        reaction = release_return(prices, item["date"])
        if reaction is None:
            skipped += 1
            continue
        usable.append({"date": item["date"], "change": item["change"], "log_return": reaction["log_return"]})
    train, hold = split(usable, lambda item: item["date"])

    def corr(items):
        return pearson([item["change"] for item in items], [item["log_return"] for item in items])

    tr, ho = corr(train), corr(hold)
    formula = (
        "Weekly change in EIA WCSSTUS1, the Strategic Petroleum Reserve, thousand barrels. "
        "Kept only when the two week-ending dates are 7 days apart. A negative change is a draw."
    )
    lead = f"Train correlation of the SPR change with the Wednesday RWTC return is {fmt_num(tr)}. Holdout correlation is {fmt_num(ho)}."
    status, line = negative_corr(tr, ho, lead)
    question = "Is the holdout correlation between the weekly SPR stock change and the Wednesday RWTC return negative?"
    entry = write_series(
        "SPR_FLOW",
        "SPR weekly stock change",
        "thousand barrels",
        "weekly",
        formula,
        ["WCSSTUS1"],
        observations,
        retrieved_at,
    )
    packed = study(
        "spr-flow",
        "20",
        "SPR flow",
        "Weekly change in the reserve",
        question,
        formula,
        status,
        line,
        bars(fmt_num(ho), "correlation", ["Train", "Holdout"], [tr, ho]),
        {
            "caption": "WCSSTUS1 weekly change versus the Wednesday RWTC log return",
            "columns": ["Window", "n", "Correlation"],
            "rows": [
                ["Train", str(len(train)), fmt_num(tr)],
                ["Holdout", str(len(hold)), fmt_num(ho)],
                ["Skipped, no Wednesday RWTC print", str(skipped), ""],
            ],
        },
        [
            "The bar is a negative holdout correlation: a draw (negative change) lining up with a higher Wednesday return.",
            "Policy announcements that are not in the stock file are not events in this test.",
        ],
        {"train_correlation": tr, "holdout_correlation": ho},
    )
    return entry, packed, card(entry, formula, question, status, line, {})


def metric_studies() -> list[dict]:
    retrieved_at = snapshot_time()
    prices = pairs(load("RWTC"))
    catalog_entries = []
    studies = []
    cards = []

    def take(result):
        entry, packed, summary = result
        if isinstance(entry, list):
            catalog_entries.extend(entry)
        else:
            catalog_entries.append(entry)
        studies.append(packed)
        cards.append(summary)

    take(surprise_and_cover(prices, retrieved_at))
    take(cushing_cover(prices, retrieved_at))
    take(curve_z(prices, retrieved_at))
    take(positioning(prices, retrieved_at))
    take(crack_gap(prices, retrieved_at))
    take(realized_vol(prices, retrieved_at))
    profile = eia_profile(prices)
    studies.append(profile)
    cards.append(
        {
            "id": "EIA_PROFILE",
            "name": "EIA-day reaction profile",
            "formula": profile["formula"],
            "unit": "log return by surprise quartile",
            "inputs": ["WCESTUS1", "RWTC"],
            "latest_date": "",
            "latest_value": profile["verdict"],
            "question": profile["question"],
            "verdict": profile["verdict"],
            "verdict_line": profile["verdict_line"],
            "constants": profile["stats"],
            "study_slug": "eia-profile",
        }
    )
    take(seasonal_stocks(prices, retrieved_at))
    take(utilization(prices, retrieved_at))
    take(spr_flow(prices, retrieved_at))
    upsert_catalog(catalog_entries)
    payload = {
        "holdout_start": HOLDOUT_START.isoformat(),
        "generated_from": "scripts/metrics.py",
        "note": "Implied volatility is absent. RV20 is realized volatility only. Every row is derived from stored government series.",
        "metrics": cards,
    }
    (ROOT / "data" / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n")
    return studies


if __name__ == "__main__":
    for item in metric_studies():
        print(f"{item['index']} {item['slug']}: {item['verdict']}")
