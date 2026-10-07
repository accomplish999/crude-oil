#!/usr/bin/env python3
"""Append a public changelog row when a stored last print changes. No row on a no-op refresh."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(catalog: dict) -> dict:
    return {
        item["id"]: {"end": item["end"], "last_value": item["last_value"], "count": item["count"]}
        for item in catalog["series"]
    }


def markdown(entries: list[dict]) -> str:
    lines = [
        "# Changelog",
        "",
        "Public record of archive refreshes. A refresh that fails validation does not add a row and does not change `main`.",
        "",
    ]
    for entry in reversed(entries):
        lines.append(f"## {entry['retrieved_at']}")
        lines.append("")
        lines.append(entry["summary"])
        lines.append("")
        if entry["changes"]:
            lines.append("| Series | Was | Now |")
            lines.append("| --- | --- | --- |")
            for change in entry["changes"]:
                lines.append(f"| {change['id']} | {change['before']} | {change['after']} |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
    path = ROOT / "data" / "changelog.json"
    payload = json.loads(path.read_text()) if path.exists() else {"entries": []}
    current = snapshot(catalog)
    previous = payload["entries"][-1]["snapshot"] if payload["entries"] else None
    changes = []
    if previous is None:
        summary = (
            f"Baseline snapshot. Retrieval {catalog['retrieved_at']}. "
            f"{len(current)} series. Validation against the source files is `scripts/verify.py`."
        )
        for series_id in sorted(current):
            item = current[series_id]
            changes.append(
                {
                    "id": series_id,
                    "before": "",
                    "after": f"{item['end']} {item['last_value']} ({item['count']} rows)",
                }
            )
    else:
        ids = sorted(set(previous) | set(current))
        for series_id in ids:
            before = previous.get(series_id)
            after = current.get(series_id)
            if before == after:
                continue
            changes.append(
                {
                    "id": series_id,
                    "before": "" if before is None else f"{before['end']} {before['last_value']}",
                    "after": "" if after is None else f"{after['end']} {after['last_value']}",
                }
            )
        if not changes:
            print("No print changed. Changelog left as it was.")
            return
        summary = f"Retrieval {catalog['retrieved_at']}. {len(changes)} series changed a last print, a row count, or both."
    payload["entries"].append(
        {
            "retrieved_at": catalog["retrieved_at"],
            "summary": summary,
            "changes": changes,
            "snapshot": current,
        }
    )
    path.write_text(json.dumps(payload, indent=2) + "\n")
    (ROOT / "CHANGELOG.md").write_text(markdown(payload["entries"]))
    print(summary)


if __name__ == "__main__":
    main()
