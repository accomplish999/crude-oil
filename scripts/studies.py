#!/usr/bin/env python3
"""Walk-forward studies. The split and the questions are fixed in this file.

Train: dates before 2020-01-01.
Holdout: dates on or after 2020-01-01.
Percentiles and month means used as rules are fit on the train window only.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logic import (  # noqa: E402
    HOLDOUT_START,
    adjacent_log_returns,
    fmt_num,
    fmt_pct,
    forward_log_return,
    is_holdout,
    mae,
    mean,
    median,
    nearest_rank,
    next_print_on_or_after,
    pairs,
    pearson,
    release_return,
    sign,
    weekly_changes,
)

SERIES = ROOT / "data" / "series"


def load(series_id: str) -> dict:
    return json.loads((SERIES / f"{series_id}.json").read_text())


def split(items, key):
    train, hold = [], []
    for item in items:
        (hold if is_holdout(key(item)) else train).append(item)
    return train, hold


def verdict(train_sign: int, hold_sign: int, label: str) -> tuple[str, str]:
    if train_sign == 0 or hold_sign == 0:
        return "flat", f"{label} The holdout mean is flat, so there is nothing to carry."
    if train_sign == hold_sign:
        return "held", f"{label} The holdout kept the train sign."
    return "failed", f"{label} The holdout flipped the train sign."


def seasonality() -> dict:
    rows = pairs(load("RWTC"))
    rets = adjacent_log_returns(rows)
    by_month = defaultdict(list)
    for item in rets:
        by_month[item["date"].month].append(item)
    table = []
    train_means = []
    hold_means = []
    for month in range(1, 13):
        train, hold = split(by_month[month], lambda item: item["date"])
        tr = mean([item["log_return"] for item in train])
        ho = mean([item["log_return"] for item in hold])
        train_means.append(tr if tr is not None else 0.0)
        hold_means.append(ho if ho is not None else 0.0)
        table.append(
            [
                f"{month:02d}",
                str(len(train)),
                fmt_pct(tr),
                str(len(hold)),
                fmt_pct(ho),
                "same" if sign(tr) == sign(ho) and sign(tr) != 0 else "not the same",
            ]
        )
    corr = pearson(train_means, hold_means)
    agree = sum(1 for row in table if row[-1] == "same")
    status = "held" if corr is not None and corr > 0 else "failed"
    line = (
        f"Correlation of the 12 train month-means with the 12 holdout month-means is {fmt_num(corr)}. "
        f"Signs match in {agree} of 12 months. "
        + (
            f"The correlation is above zero, which was the bar. {agree} matching signs out of 12 is a thin map."
            if status == "held"
            else "The seasonal map did not repeat. A positive correlation was the precommitted bar."
        )
    )
    return {
        "slug": "seasonality",
        "index": "01",
        "title": "Seasonality",
        "kicker": "Calendar month",
        "question": "Do WTI's calendar-month mean returns from before 2020 show up again after it?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_num(corr),
            "stat_label": "train vs holdout month-mean correlation",
            "categories": [f"{month:02d}" for month in range(1, 13)],
            "series": [
                {"name": "Train mean daily log return", "values": train_means},
                {"name": "Holdout mean daily log return", "values": hold_means},
            ],
        },
        "table": {
            "caption": "Mean daily log return of RWTC by calendar month",
            "columns": ["Month", "Train n", "Train mean", "Holdout n", "Holdout mean", "Sign"],
            "rows": table,
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "The question is whether the calendar still matters after the sample that drew the map.",
                    "Series is EIA RWTC, Cushing WTI spot, dollars per barrel. The return is the log change between two published prints at most five calendar days apart. Longer holes are dropped.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "Train prints end 31 Dec 2019. Holdout prints start 1 Jan 2020. Each calendar month gets a mean daily log return in each window.",
                    "The precommitted score is the Pearson correlation of the 12 train means with the 12 holdout means. Above zero, the map repeated. At or below zero, it did not. No month is dropped after the fact.",
                ],
            },
            {
                "label": "Result",
                "body": [
                    line,
                    f"Train daily returns used: {sum(int(row[1]) for row in table)}. Holdout daily returns used: {sum(int(row[3]) for row in table)}.",
                ],
            },
        ],
        "stats": {"correlation": corr, "sign_matches": agree},
    }


def inventory_panel(stock_id: str, slug: str, index: str, title: str, kicker: str) -> dict:
    stocks = weekly_changes(pairs(load(stock_id)))
    prices = pairs(load("RWTC"))
    usable = []
    skipped_release = 0
    for change in stocks:
        shock_window = [item["change"] for item in stocks if item["date"] < change["date"]][-52:]
        if len(shock_window) < 52:
            continue
        baseline = median(shock_window)
        surprise = change["change"] - baseline
        reaction = release_return(prices, change["date"])
        if reaction is None:
            skipped_release += 1
            continue
        usable.append({**change, "surprise": surprise, "log_return": reaction["log_return"], "release": reaction["release"]})
    train, hold = split(usable, lambda item: item["release"])
    def corr(items):
        return pearson([item["surprise"] for item in items], [item["log_return"] for item in items])
    tr = corr(train)
    ho = corr(hold)
    # Precommitted bar: holdout correlation is negative.
    if ho is None:
        status = "flat"
        tail = "The holdout correlation is undefined."
    elif ho < 0:
        status = "held"
        tail = "The holdout correlation is negative, which was the bar."
        if tr is not None and tr >= 0:
            tail += " The train correlation was not negative, so the in-sample half never showed the same pressure."
    else:
        status = "failed"
        tail = "The holdout correlation is not negative. The bar was missed."
    line = (
        f"Train correlation of surprise with the release-day RWTC log return is {fmt_num(tr)}. "
        f"Holdout correlation is {fmt_num(ho)}. {tail}"
    )
    return {
        "slug": slug,
        "index": index,
        "title": title,
        "kicker": kicker,
        "question": f"Does a {stock_id} build versus its own prior 52 weeks show up as a lower RWTC print on the nominal EIA Wednesday?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_num(ho),
            "stat_label": "holdout correlation, surprise vs release-day return",
            "categories": ["Train", "Holdout"],
            "series": [{"name": "Correlation", "values": [tr or 0, ho or 0]}],
        },
        "table": {
            "caption": f"{stock_id} surprise versus RWTC release-day log return",
            "columns": ["Window", "n", "Correlation"],
            "rows": [
                ["Train, release before 2020-01-01", str(len(train)), fmt_num(tr)],
                ["Holdout, release on or after 2020-01-01", str(len(hold)), fmt_num(ho)],
                ["Skipped, no Wednesday RWTC print", str(skipped_release), ""],
            ],
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    f"Stocks are EIA {stock_id}. The change is this week minus last week, and only when the week-ending dates are seven days apart.",
                    "The baseline is the median change of the prior 52 kept weeks. Surprise is the current change minus that median. It is not an analyst survey.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "The EIA week ends Friday. The nominal release is the Wednesday five days later. The price is the log change from the last RWTC print before that Wednesday to the print on that Wednesday. If Wednesday has no print, the week is skipped. Thursday holiday releases are not moved.",
                    "The precommitted sign is negative: a positive surprise (a bigger build, or a smaller draw, than the prior 52 weeks) should come with a negative release-day return. Train and holdout correlations are scored separately. The holdout fails if it is not negative.",
                ],
            },
            {
                "label": "Result",
                "body": [
                    line,
                    f"Usable weeks in train: {len(train)}. Usable weeks in holdout: {len(hold)}. Weeks skipped because Wednesday had no RWTC print: {skipped_release}.",
                ],
            },
        ],
        "stats": {
            "train_correlation": tr,
            "holdout_correlation": ho,
            "n_train": len(train),
            "n_holdout": len(hold),
            "skipped_release": skipped_release,
        },
    }


def term_structure() -> dict:
    spread_rows = pairs(load("CL1_MINUS_CL4"))
    prices = pairs(load("RWTC"))
    usable = []
    for day, spread in spread_rows:
        forward = forward_log_return(prices, day, 5)
        if forward is None:
            continue
        usable.append({"date": day, "spread": spread, "forward": forward, "backwardation": spread > 0})
    train, hold = split(usable, lambda item: item["date"])

    def gap(items):
        back = [item["forward"] for item in items if item["backwardation"]]
        cont = [item["forward"] for item in items if not item["backwardation"]]
        b, c = mean(back), mean(cont)
        if b is None or c is None:
            return None, b, c, len(back), len(cont)
        return b - c, b, c, len(back), len(cont)

    tr, tr_b, tr_c, tr_nb, tr_nc = gap(train)
    ho, ho_b, ho_c, ho_nb, ho_nc = gap(hold)
    status, line = verdict(
        sign(tr),
        sign(ho),
        f"Train mean five-print RWTC return in backwardation minus contango is {fmt_pct(tr)}. Holdout difference is {fmt_pct(ho)}. "
        "A negative gap means backwardation did not pay more than contango.",
    )
    return {
        "slug": "term-structure",
        "index": "03",
        "title": "Term structure",
        "kicker": "Contract 1 minus contract 4",
        "question": "Does the gap between five-print RWTC returns in backwardation and in contango keep its sign after 2019?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_pct(ho),
            "stat_label": "holdout backwardation minus contango, five-print return",
            "categories": ["Train back", "Train contango", "Holdout back", "Holdout contango"],
            "series": [{"name": "Mean five-print log return", "values": [tr_b or 0, tr_c or 0, ho_b or 0, ho_c or 0]}],
        },
        "table": {
            "caption": "Five-print RWTC log return by the sign of RCLC1 minus RCLC4",
            "columns": ["Window", "State", "n", "Mean return"],
            "rows": [
                ["Train", "Backwardation (spread > 0)", str(tr_nb), fmt_pct(tr_b)],
                ["Train", "Contango (spread < 0)", str(tr_nc), fmt_pct(tr_c)],
                ["Holdout", "Backwardation (spread > 0)", str(ho_nb), fmt_pct(ho_b)],
                ["Holdout", "Contango (spread < 0)", str(ho_nc), fmt_pct(ho_c)],
            ],
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "The curve in this archive is four EIA series: RCLC1, RCLC2, RCLC3, RCLC4. The spread is contract 1 minus contract 4. Positive means the front is above the fourth.",
                    f"RCLC1 in this snapshot last prints on {load('RCLC1')['observations'][-1]['date']}. That is the last row of EIA's history workbook on the day it was fetched. The series is not extended to the spot date.",
                    "A full exchange board is not in the archive. Exchange quotes are licensed. Four months is what EIA posts for free.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "On each day both the spread and RWTC print, take the log change in RWTC five published prints later. Split the days by the sign of the spread.",
                    "The precommitted score is the mean five-print return in backwardation minus the mean in contango. The holdout uses the same sign rule. It fails if that difference changes sign.",
                ],
            },
            {
                "label": "Result",
                "body": [line],
            },
        ],
        "stats": {"train_diff": tr, "holdout_diff": ho},
    }


def positioning() -> dict:
    series = load("CFTC_CL")
    prices = pairs(load("RWTC"))
    rows = []
    for obs in series["observations"]:
        day = date.fromisoformat(obs["date"])
        anchor = next_print_on_or_after(prices, day, 3)
        if anchor is None:
            continue
        forward = forward_log_return(prices, anchor, 5)
        if forward is None:
            continue
        rows.append(
            {
                "date": day,
                "net_oi": float(obs["mm_net_oi"]),
                "forward": forward,
                "mm_net": obs["mm_net"],
                "open_interest": obs["open_interest"],
            }
        )
    train, hold = split(rows, lambda item: item["date"])
    threshold = nearest_rank([item["net_oi"] for item in train], 0.9)
    def side(items, above: bool):
        picked = [item["forward"] for item in items if (item["net_oi"] >= threshold) == above]
        return mean(picked), len(picked)
    tr_hi, tr_nh = side(train, True)
    tr_lo, tr_nl = side(train, False)
    ho_hi, ho_nh = side(hold, True)
    ho_lo, ho_nl = side(hold, False)
    tr = None if tr_hi is None or tr_lo is None else tr_hi - tr_lo
    ho = None if ho_hi is None or ho_lo is None else ho_hi - ho_lo
    status, line = verdict(
        sign(tr),
        sign(ho),
        f"The frozen 90th percentile of managed-money net over open interest is {fmt_num(threshold, 4)}. "
        f"Train five-print return above that line minus the return below it is {fmt_pct(tr)}. Holdout difference is {fmt_pct(ho)}.",
    )
    return {
        "slug": "positioning",
        "index": "04",
        "title": "COT positioning",
        "kicker": "Managed money on 067651",
        "question": "After managed money net on WTI-PHYSICAL is extremely long versus the pre-2020 book, is the next five-print RWTC return higher?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_num(threshold, 4),
            "stat_label": "frozen train 90th percentile, net / open interest",
            "categories": ["Train extreme", "Train rest", "Holdout extreme", "Holdout rest"],
            "series": [{"name": "Mean five-print log return", "values": [tr_hi or 0, tr_lo or 0, ho_hi or 0, ho_lo or 0]}],
        },
        "table": {
            "caption": "Five-print RWTC return after CFTC_CL managed-money net / open interest",
            "columns": ["Window", "Bucket", "n", "Mean return"],
            "rows": [
                ["Train", f"At or above {fmt_num(threshold, 4)}", str(tr_nh), fmt_pct(tr_hi)],
                ["Train", "Below the frozen line", str(tr_nl), fmt_pct(tr_lo)],
                ["Holdout", f"At or above {fmt_num(threshold, 4)}", str(ho_nh), fmt_pct(ho_hi)],
                ["Holdout", "Below the frozen line", str(ho_nl), fmt_pct(ho_lo)],
            ],
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "Positions are CFTC disaggregated futures, contract market code 067651. The report calls it WTI-PHYSICAL on the New York Mercantile Exchange. Older rows in the same code used a longer name. The code is the join.",
                    "Managed money net is long minus short. Spreads stay in their own column and are not added in. The ratio divides that net by open interest.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "The 90th percentile is the nearest rank of the train ratios only. The holdout is cut with that same number.",
                    "The return is five published RWTC prints after the first RWTC print on or within three days after the report date. The precommitted score is the mean return above the line minus the mean return below it. A sign change is a miss.",
                ],
            },
            {
                "label": "Result",
                "body": [line],
            },
        ],
        "stats": {"threshold": threshold, "train_diff": tr, "holdout_diff": ho},
    }


def report_day() -> dict:
    rets = adjacent_log_returns(pairs(load("RWTC")))
    def is_nominal_wednesday(item):
        return item["date"].weekday() == 2
    train, hold = split(rets, lambda item: item["date"])
    def ratio(items):
        wed = [abs(item["log_return"]) for item in items if is_nominal_wednesday(item)]
        other = [abs(item["log_return"]) for item in items if not is_nominal_wednesday(item)]
        w, o = mean(wed), mean(other)
        if w is None or o is None or o == 0:
            return None, w, o, len(wed), len(other)
        return w / o, w, o, len(wed), len(other)
    tr, tr_w, tr_o, tr_nw, tr_no = ratio(train)
    ho, ho_w, ho_o, ho_nw, ho_no = ratio(hold)
    # Precommitted: Wednesday absolute return / other-day absolute return stays above 1.
    status = "held" if tr is not None and ho is not None and tr > 1 and ho > 1 else "failed"
    line = (
        f"Train ratio of mean absolute Wednesday log return to other days is {fmt_num(tr)}. "
        f"Holdout ratio is {fmt_num(ho)}. "
        + (
            "Both windows clear 1, which was the bar. The margin is small."
            if status == "held"
            else "The bar was a ratio above 1 in both windows. It was missed."
        )
    )
    return {
        "slug": "report-day",
        "index": "05",
        "title": "EIA report day",
        "kicker": "Wednesday absolute return",
        "question": "Is the absolute RWTC move larger on Wednesdays than on other published days, in both windows?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_num(ho),
            "stat_label": "holdout Wednesday absolute return / other days",
            "categories": ["Train Wed", "Train other", "Holdout Wed", "Holdout other"],
            "series": [{"name": "Mean absolute log return", "values": [tr_w or 0, tr_o or 0, ho_w or 0, ho_o or 0]}],
        },
        "table": {
            "caption": "Mean absolute adjacent RWTC log return",
            "columns": ["Window", "Day", "n", "Mean absolute return"],
            "rows": [
                ["Train", "Wednesday", str(tr_nw), fmt_pct(tr_w)],
                ["Train", "Other published days", str(tr_no), fmt_pct(tr_o)],
                ["Holdout", "Wednesday", str(ho_nw), fmt_pct(ho_w)],
                ["Holdout", "Other published days", str(ho_no), fmt_pct(ho_o)],
            ],
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "The nominal Weekly Petroleum Status Report hits on Wednesday at 10:30 Eastern. This study does not have a holiday calendar, so it does not move the label when EIA publishes Thursday.",
                    "A Wednesday here is a published RWTC print whose date falls on Wednesday. The return is the adjacent log change ending that day.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "Compare the mean absolute log return on those Wednesdays with the mean absolute log return on every other published day.",
                    "The precommitted bar is a ratio above 1 in the train window and again in the holdout. One window above 1 is not enough.",
                ],
            },
            {
                "label": "Result",
                "body": [line],
            },
        ],
        "stats": {"train_ratio": tr, "holdout_ratio": ho},
    }


def crack() -> dict:
    crack_rows = pairs(load("CRACK_321"))
    prices = pairs(load("RWTC"))
    usable = []
    for day, level in crack_rows:
        forward = forward_log_return(prices, day, 5)
        if forward is None:
            continue
        usable.append({"date": day, "level": level, "forward": forward})
    train, hold = split(usable, lambda item: item["date"])
    tr = pearson([item["level"] for item in train], [item["forward"] for item in train])
    ho = pearson([item["level"] for item in hold], [item["forward"] for item in hold])
    status, line = verdict(
        sign(tr),
        sign(ho),
        f"Train correlation of the 3-2-1 crack with the next five-print RWTC return is {fmt_num(tr)}. Holdout correlation is {fmt_num(ho)}.",
    )
    return {
        "slug": "crack",
        "index": "07",
        "title": "Crack spread",
        "kicker": "3-2-1 from EIA futures",
        "question": "Does a richer 3-2-1 crack line up with a higher five-print RWTC return, and does that sign survive 2020?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_num(ho),
            "stat_label": "holdout correlation, crack level vs five-print RWTC return",
            "categories": ["Train", "Holdout"],
            "series": [{"name": "Correlation", "values": [tr or 0, ho or 0]}],
        },
        "table": {
            "caption": "CRACK_321 level versus the next five RWTC prints",
            "columns": ["Window", "n", "Correlation"],
            "rows": [
                ["Train", str(len(train)), fmt_num(tr)],
                ["Holdout", str(len(hold)), fmt_num(ho)],
            ],
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "The crack is ((2 * RBOB_F1 + HO_F1) / 3) * 42 minus RCLC1. RBOB and heating oil are EIA futures in dollars per gallon. Times 42 puts them on a barrel. Contract 1 crude is dollars per barrel.",
                    f"The last crack date in this snapshot is {load('CRACK_321')['observations'][-1]['date']}, which is the last day all three EIA futures print together.",
                    "A date is kept only when all three inputs print. Nothing is filled.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "The theory under test is simple: a wide crack pulls refinery demand for crude, so the next RWTC return should be positive when the crack is high. The score is the correlation of the crack level with the five-print RWTC log return.",
                    "The holdout fails if that correlation is not positive.",
                ],
            },
            {
                "label": "Result",
                "body": [line, f"Train days: {len(train)}. Holdout days: {len(hold)}."],
            },
        ],
        "stats": {"train_correlation": tr, "holdout_correlation": ho},
    }


def events() -> dict:
    stocks = weekly_changes(pairs(load("WCESTUS1")))
    prices = pairs(load("RWTC"))
    surprises = []
    for change in stocks:
        window = [item["change"] for item in stocks if item["date"] < change["date"]][-52:]
        if len(window) < 52:
            continue
        surprise = change["change"] - median(window)
        reaction = release_return(prices, change["date"])
        if reaction is None:
            continue
        forward = forward_log_return(prices, reaction["release"], 5)
        if forward is None:
            continue
        surprises.append({"date": reaction["release"], "surprise": surprise, "forward": forward})
    train, hold = split(surprises, lambda item: item["date"])
    lo = nearest_rank([item["surprise"] for item in train], 0.1)
    hi = nearest_rank([item["surprise"] for item in train], 0.9)
    def bucket(items, which):
        if which == "build":
            picked = [item["forward"] for item in items if item["surprise"] >= hi]
        elif which == "draw":
            picked = [item["forward"] for item in items if item["surprise"] <= lo]
        else:
            picked = [item["forward"] for item in items if lo < item["surprise"] < hi]
        return mean(picked), len(picked)
    rows = []
    stats = {"low": lo, "high": hi}
    for window_name, items in (("Train", train), ("Holdout", hold)):
        for which in ("draw", "middle", "build"):
            avg, n = bucket(items, which)
            stats[f"{window_name.lower()}_{which}"] = avg
            stats[f"{window_name.lower()}_{which}_n"] = n
            rows.append([window_name, which, str(n), fmt_pct(avg)])
    # Precommitted: holdout draw events have a higher five-print return than holdout build events.
    ho_draw = stats["holdout_draw"]
    ho_build = stats["holdout_build"]
    diff = None if ho_draw is None or ho_build is None else ho_draw - ho_build
    tr_diff = None
    if stats["train_draw"] is not None and stats["train_build"] is not None:
        tr_diff = stats["train_draw"] - stats["train_build"]
    status, line = verdict(
        sign(tr_diff),
        sign(diff),
        f"Frozen train tails are {fmt_num(lo, 0)} and {fmt_num(hi, 0)} thousand barrels. "
        f"Train draw-minus-build five-print return is {fmt_pct(tr_diff)}. Holdout difference is {fmt_pct(diff)}. "
        "A negative number means the draw tail was followed by a lower return than the build tail.",
    )
    return {
        "slug": "events",
        "index": "08",
        "title": "Inventory tails",
        "kicker": "Train deciles, frozen",
        "question": "Do the outer deciles of the WCESTUS1 surprise, cut on the train window only, still separate five-print RWTC returns after 2019?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_pct(diff),
            "stat_label": "holdout draw minus build, five-print return",
            "categories": ["Train draw", "Train build", "Holdout draw", "Holdout build"],
            "series": [
                {
                    "name": "Mean five-print log return",
                    "values": [
                        stats["train_draw"] or 0,
                        stats["train_build"] or 0,
                        stats["holdout_draw"] or 0,
                        stats["holdout_build"] or 0,
                    ],
                }
            ],
        },
        "table": {
            "caption": "Five-print RWTC return by frozen WCESTUS1 surprise tail",
            "columns": ["Window", "Tail", "n", "Mean return"],
            "rows": rows,
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "An event here is mechanical. It is not a war, a meeting, or a headline. Those dates are not in a public file this archive can store without editorial selection.",
                    "Surprise is the weekly change in US crude stocks excluding the SPR, minus the median of the prior 52 seven-day changes.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "The 10th and 90th percentiles are nearest ranks of the train surprises. Holdout weeks are labeled with those two numbers.",
                    "The return is five published RWTC prints after the nominal Wednesday release. The score is the mean return in the draw tail minus the mean return in the build tail. The holdout fails if that difference changes sign.",
                ],
            },
            {
                "label": "Result",
                "body": [line],
            },
        ],
        "stats": {"train_diff": tr_diff, "holdout_diff": diff, "low": lo, "high": hi},
    }


def anomalies() -> dict:
    rets = adjacent_log_returns(pairs(load("RWTC")))
    train, hold = split(rets, lambda item: item["date"])
    train_values = [item["log_return"] for item in train]
    center = median(train_values)
    mad = median([abs(value - center) for value in train_values])
    scale = 1.4826 * mad
    prices = pairs(load("RWTC"))
    flagged = []
    quiet = []
    for item in hold:
        if scale == 0:
            break
        zed = abs(item["log_return"] - center) / scale
        forward = forward_log_return(prices, item["date"], 5)
        if forward is None:
            continue
        bucket = flagged if zed > 4 else quiet
        bucket.append(abs(forward))
    f_mean, q_mean = mean(flagged), mean(quiet)
    diff = None if f_mean is None or q_mean is None else f_mean - q_mean
    status = "held" if diff is not None and diff > 0 else "failed"
    line = (
        f"Train median daily log return is {fmt_pct(center)}. MAD scale is {fmt_pct(scale)}. "
        f"Holdout days with |z| above 4: {len(flagged)}. "
        f"Their mean absolute five-print return is {fmt_pct(f_mean)}, against {fmt_pct(q_mean)} on the other holdout days. "
        + (
            "The flagged days were followed by larger absolute moves."
            if status == "held"
            else "The flagged days were not followed by larger absolute moves. The detector described the day. It did not lead the next week."
        )
        + " The holdout contains the 2020 break, and a large print often sits next to another large print."
    )
    return {
        "slug": "anomalies",
        "index": "09",
        "title": "Anomaly flags",
        "kicker": "Train median and MAD",
        "question": "Do RWTC days that sit more than four robust z-scores from the pre-2020 center lead larger five-print absolute moves?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": str(len(flagged)),
            "stat_label": "holdout days with |z| > 4",
            "categories": ["Flagged", "Other holdout days"],
            "series": [{"name": "Mean absolute five-print log return", "values": [f_mean or 0, q_mean or 0]}],
        },
        "table": {
            "caption": "Holdout RWTC days scored with the frozen train center and MAD",
            "columns": ["Bucket", "n", "Mean absolute five-print return"],
            "rows": [
                ["|z| > 4", str(len(flagged)), fmt_pct(f_mean)],
                ["The rest of the holdout", str(len(quiet)), fmt_pct(q_mean)],
            ],
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "The flag is a robust z-score. Center is the train median of adjacent daily log returns. Scale is 1.4826 times the train median absolute deviation. Both numbers are frozen.",
                    "A flag is descriptive. The test is whether the next five published prints move more, in absolute log return, after a flag than after an ordinary holdout day.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "Holdout days with |z| above 4 are the flags. The bar is a higher mean absolute five-print return on flags than on the other holdout days.",
                    "No new cutoff is chosen after seeing the holdout.",
                ],
            },
            {
                "label": "Result",
                "body": [line],
            },
        ],
        "stats": {"center": center, "scale": scale, "n_flags": len(flagged), "flag_mean": f_mean, "quiet_mean": q_mean},
    }


def rwtc_month_panel() -> list[dict]:
    """Monthly RWTC log returns and the frozen pre-2020 calendar mean.

    A month's realized log return is the sum of adjacent daily log returns
    whose end date falls in that month. Holdout months start 2020-01-01.
    The calendar mean for a month is fit on earlier years of that same
    calendar month, and it is not updated during the holdout.
    """
    rets = adjacent_log_returns(pairs(load("RWTC")))
    monthly = defaultdict(float)
    for item in rets:
        key = (item["date"].year, item["date"].month)
        monthly[key] += item["log_return"]
    months = sorted(monthly)
    train_by_cal = defaultdict(list)
    rows = []
    for year, month in months:
        stamp = date(year, month, 1)
        realized = monthly[(year, month)]
        if stamp < HOLDOUT_START:
            train_by_cal[month].append(realized)
            continue
        seasonal = mean(train_by_cal[month])
        if seasonal is None:
            continue
        history = [monthly[key] for key in months if key < (year, month)]
        rows.append(
            {
                "year": year,
                "month": month,
                "realized": realized,
                "seasonal": seasonal,
                "history": history,
            }
        )
    return rows


def forecast() -> dict:
    panel = rwtc_month_panel()
    hold_errors_flat = [row["realized"] - 0.0 for row in panel]
    hold_errors_season = [row["realized"] - row["seasonal"] for row in panel]
    flat = mae(hold_errors_flat)
    seasonal_mae = mae(hold_errors_season)
    status = "held" if seasonal_mae is not None and flat is not None and seasonal_mae < flat else "failed"
    edge = None if seasonal_mae is None or flat is None else flat - seasonal_mae
    line = (
        f"Holdout months: {len(hold_errors_flat)}. "
        f"Mean absolute error of the train calendar-month mean is {fmt_pct(seasonal_mae)}. "
        f"Mean absolute error of a flat zero forecast is {fmt_pct(flat)}. "
        f"The difference is {fmt_pct(edge)}. "
        + (
            "The calendar mean is lower error, which was the bar."
            if status == "held"
            else "The calendar mean lost to a forecast of zero. That is the forecast result."
        )
    )
    times_note = (
        "TimesFM is not in this run. The script is scripts/timesfm_study.py. "
        "It downloads the open weights at runtime and writes data/timesfm.json. "
        "Until that file exists, the experimental forecast is absent, and the holdout above is the one that counts."
    )
    categories = ["Seasonal naive", "Flat zero"]
    values = [seasonal_mae or 0, flat or 0]
    table_rows = [
        ["Train mean for that calendar month", str(len(hold_errors_season)), fmt_pct(seasonal_mae)],
        ["Flat zero", str(len(hold_errors_flat)), fmt_pct(flat)],
    ]
    extra_stats = {}
    times_path = ROOT / "data" / "timesfm.json"
    if times_path.exists():
        times = json.loads(times_path.read_text())
        same_n = times.get("n") == len(hold_errors_flat)
        same_season = seasonal_mae is not None and abs(times.get("seasonal_mae", 0) - seasonal_mae) < 1e-9
        same_flat = flat is not None and abs(times.get("flat_mae", 0) - flat) < 1e-9
        if same_n and same_season and same_flat and isinstance(times.get("timesfm_mae"), (int, float)):
            times_note = times["summary"]
            categories.append("TimesFM median")
            values.append(times["timesfm_mae"])
            table_rows.append(
                ["TimesFM median, one month ahead", str(times["n"]), fmt_pct(times["timesfm_mae"])]
            )
            extra_stats = {"timesfm_mae": times["timesfm_mae"]}
        else:
            times_note = (
                "data/timesfm.json is present, and it does not match this holdout. "
                "The experimental row is omitted. The calendar mean against zero is still the result."
            )
    return {
        "slug": "forecast",
        "index": "10",
        "title": "Forecast",
        "kicker": "Seasonal naive against zero",
        "question": "On holdout months, does the pre-2020 mean for that calendar month beat a forecast of a zero monthly log return?",
        "verdict": status,
        "verdict_line": line,
        "chart": {
            "type": "bars",
            "stat": fmt_pct(seasonal_mae),
            "stat_label": "holdout MAE, seasonal naive",
            "categories": categories,
            "series": [{"name": "Holdout mean absolute error", "values": values}],
        },
        "table": {
            "caption": "Holdout monthly RWTC log return, mean absolute error",
            "columns": ["Forecast", "Holdout months", "MAE"],
            "rows": table_rows,
        },
        "cells": [
            {
                "label": "Question",
                "body": [
                    "A month's realized log return is the sum of the adjacent daily RWTC log returns whose end date falls in that month.",
                    "The seasonal naive predicts the mean of train months with the same calendar month. The flat forecast predicts zero. Both are fixed before the holdout is scored.",
                ],
            },
            {
                "label": "Method",
                "body": [
                    "Mean absolute error on holdout months decides it. The seasonal forecast has to be strictly lower error than zero.",
                    times_note,
                ],
            },
            {
                "label": "Result",
                "body": [line, times_note],
            },
        ],
        "stats": {
            "seasonal_mae": seasonal_mae,
            "flat_mae": flat,
            "n": len(hold_errors_flat),
            **extra_stats,
        },
    }


def main() -> None:
    from metrics import metric_studies

    studies = [
        seasonality(),
        inventory_panel("WCESTUS1", "inventory", "02", "Inventory surprise", "Stocks ex-SPR vs the prior 52 weeks"),
        term_structure(),
        positioning(),
        report_day(),
        inventory_panel("CUSHING", "cushing", "06", "Cushing", "Cushing stocks vs the prior 52 weeks"),
        crack(),
        events(),
        anomalies(),
        forecast(),
    ]
    studies.extend(metric_studies())
    payload = {
        "holdout_start": HOLDOUT_START.isoformat(),
        "generated_from": "scripts/studies.py",
        "studies": studies,
    }
    path = ROOT / "data" / "studies.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    for study in studies:
        print(f"{study['index']} {study['slug']}: {study['verdict']}")


if __name__ == "__main__":
    main()
