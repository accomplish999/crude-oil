"""Alignment and summary math. No fills. Thresholds come from the train window only."""

from __future__ import annotations

import math
import statistics
from datetime import date, datetime, timedelta

HOLDOUT_START = date(2020, 1, 1)
MAX_GAP_DAYS = 5


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def is_holdout(value: date) -> bool:
    return value >= HOLDOUT_START


def canon_number(value: float) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text in {"", "."}:
            raise ValueError("empty")
        return text
    if not math.isfinite(value):
        raise ValueError("non-finite")
    nearest = round(value)
    if abs(value - nearest) < 1e-9 and abs(value) < 1e15:
        return str(int(nearest))
    # Shortest decimal that round-trips. A loose tolerance will turn 86.91 into 86.9.
    for digits in range(0, 10):
        text = f"{value:.{digits}f}"
        if abs(float(text) - value) < 1e-9:
            return text
    return format(value, ".12g")


def as_float(text: str) -> float:
    return float(text)


def pairs(series: dict) -> list[tuple[date, float]]:
    field = "value"
    rows = []
    for row in series["observations"]:
        if field not in row:
            continue
        rows.append((parse_date(row["date"]), as_float(row[field])))
    rows.sort(key=lambda item: item[0])
    return rows


def index_by_date(rows: list[tuple[date, float]]) -> dict[date, float]:
    return {day: value for day, value in rows}


def adjacent_log_returns(rows: list[tuple[date, float]]) -> list[dict]:
    """Log change between published prints at most MAX_GAP_DAYS apart."""
    out = []
    for (d0, v0), (d1, v1) in zip(rows, rows[1:]):
        gap = (d1 - d0).days
        if gap < 1 or gap > MAX_GAP_DAYS or v0 <= 0 or v1 <= 0:
            continue
        out.append(
            {
                "date": d1,
                "prev": d0,
                "gap": gap,
                "log_return": math.log(v1 / v0),
            }
        )
    return out


def weekly_changes(rows: list[tuple[date, float]]) -> list[dict]:
    out = []
    skipped = 0
    for (d0, v0), (d1, v1) in zip(rows, rows[1:]):
        if (d1 - d0).days != 7:
            skipped += 1
            continue
        out.append({"date": d1, "prev": d0, "change": v1 - v0, "level": v1})
    return out


def release_wednesday(week_ending: date) -> date:
    """EIA week ends Friday. The nominal release is the following Wednesday."""
    return week_ending + timedelta(days=5)


def print_on(rows: list[tuple[date, float]], day: date) -> float | None:
    for stamp, value in rows:
        if stamp == day:
            return value
    return None


def prior_print(rows: list[tuple[date, float]], day: date) -> tuple[date, float] | None:
    found = None
    for stamp, value in rows:
        if stamp < day:
            found = (stamp, value)
        else:
            break
    return found


def release_return(price_rows: list[tuple[date, float]], week_ending: date) -> dict | None:
    release = release_wednesday(week_ending)
    spot = print_on(price_rows, release)
    if spot is None:
        return None
    prev = prior_print(price_rows, release)
    if prev is None:
        return None
    prev_day, prev_px = prev
    gap = (release - prev_day).days
    if gap < 1 or gap > MAX_GAP_DAYS or prev_px <= 0 or spot <= 0:
        return None
    return {
        "release": release,
        "prev": prev_day,
        "gap": gap,
        "log_return": math.log(spot / prev_px),
    }


def forward_log_return(rows: list[tuple[date, float]], start: date, steps: int) -> float | None:
    dates = [day for day, _ in rows]
    try:
        idx = dates.index(start)
    except ValueError:
        return None
    j = idx + steps
    if j >= len(rows):
        return None
    v0 = rows[idx][1]
    v1 = rows[j][1]
    if v0 <= 0 or v1 <= 0:
        return None
    return math.log(v1 / v0)


def next_print_on_or_after(rows: list[tuple[date, float]], day: date, limit: int = 3) -> date | None:
    for stamp, _ in rows:
        if stamp < day:
            continue
        if (stamp - day).days <= limit:
            return stamp
        return None
    return None


def median(values: list[float]) -> float:
    return statistics.median(values)


def mad_scale(values: list[float]) -> tuple[float, float]:
    """Train center and robust scale. Scale is 1.4826 times the median absolute deviation."""
    center = median(values)
    mad = median([abs(value - center) for value in values])
    return center, 1.4826 * mad


def nearest_rank(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty")
    rank = math.ceil(p * len(ordered)) - 1
    rank = min(max(rank, 0), len(ordered) - 1)
    return ordered[rank]


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def mae(errors: list[float]) -> float | None:
    if not errors:
        return None
    return sum(abs(item) for item in errors) / len(errors)


def fmt_num(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_pct(log_value: float | None, digits: int = 3) -> str:
    """Format a log return as percent."""
    if log_value is None:
        return "n/a"
    return f"{log_value * 100:.{digits}f}%"


def sign(value: float | None) -> int:
    if value is None or value == 0:
        return 0
    return 1 if value > 0 else -1
