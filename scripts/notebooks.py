#!/usr/bin/env python3
"""Write one Jupyter notebook per study. Outputs are the stored results, not a second model."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_lines(text: str) -> list[str]:
    lines = text.split("\n")
    out = [f"{line}\n" for line in lines[:-1]]
    if lines[-1] != "" or len(lines) == 1:
        out.append(lines[-1])
    return out


def notebook(study: dict, holdout: str) -> dict:
    formula = study.get("formula") or "This study reads stored series. It does not add a derived column."
    method = "\n\n".join(cell["body"][0] if cell["body"] else "" for cell in study["cells"] if cell["label"] == "Method")
    code = (
        "import json\n"
        "from pathlib import Path\n"
        f"studies = json.loads(Path('data/studies.json').read_text())\n"
        f"study = next(item for item in studies['studies'] if item['slug'] == {study['slug']!r})\n"
        "print(study['verdict'])\n"
        "print(study['verdict_line'])\n"
        "print(study['table']['caption'])\n"
        "for row in study['table']['rows']:\n"
        "    print(' | '.join(row))\n"
    )
    stdout = study["verdict"] + "\n" + study["verdict_line"] + "\n" + study["table"]["caption"] + "\n"
    stdout += "\n".join(" | ".join(row) for row in study["table"]["rows"]) + "\n"
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": source_lines(
                    f"# {study['index']} {study['title']}\n\n"
                    f"{study['question']}\n\n"
                    f"Holdout starts {holdout}. Verdict: {study['verdict']}.\n\n"
                    f"{formula}"
                ),
            },
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "source": source_lines(code),
                "outputs": [{"output_type": "stream", "name": "stdout", "text": source_lines(stdout)}],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": source_lines(f"## Method\n\n{method}\n\n## Result\n\n{study['verdict_line']}"),
            },
        ],
    }


def main() -> None:
    studies = json.loads((ROOT / "data" / "studies.json").read_text())
    folder = ROOT / "notebooks"
    folder.mkdir(parents=True, exist_ok=True)
    public = ROOT / "public" / "notebooks"
    public.mkdir(parents=True, exist_ok=True)
    keep = set()
    for study in studies["studies"]:
        name = f"{study['index']}-{study['slug']}.ipynb"
        payload = json.dumps(notebook(study, studies["holdout_start"]), indent=2) + "\n"
        (folder / name).write_text(payload)
        (public / name).write_text(payload)
        keep.add(name)
        print(name)
    for path in list(folder.glob("*.ipynb")) + list(public.glob("*.ipynb")):
        if path.name not in keep:
            path.unlink()


if __name__ == "__main__":
    main()
