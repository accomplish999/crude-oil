#!/usr/bin/env python3
"""Experimental TimesFM forecast on the same monthly RWTC holdout.

The seasonal-naive rule in scripts/studies.py is unchanged. This script
downloads the open weights, writes data/timesfm.json, and stops if the
package or the checkpoint is missing. It does not invent a forecast.

Protocol, fixed before the run:
- Target: one holdout month of RWTC log return, same months as the seasonal study.
- Point: the model's median quantile. Negative values are allowed.
- Context: every completed month strictly before the target month.
- Score: mean absolute error on those holdout months, beside the frozen
  pre-2020 calendar mean and a flat zero.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from logic import fmt_pct, mae  # noqa: E402
from studies import rwtc_month_panel  # noqa: E402

MODEL_ID = "google/timesfm-3.0-pytorch"
OUT = ROOT / "data" / "timesfm.json"


def summary(n: int, timesfm_mae: float, seasonal_mae: float, flat_mae: float) -> str:
    if timesfm_mae < seasonal_mae:
        relation = "lower"
    elif timesfm_mae > seasonal_mae:
        relation = "higher"
    else:
        relation = "the same"
    return (
        f"TimesFM 3.0 median, one month ahead, expanding history. "
        f"Holdout months: {n}. "
        f"TimesFM mean absolute error is {fmt_pct(timesfm_mae)}. "
        f"The train calendar-month mean is {fmt_pct(seasonal_mae)}. "
        f"A flat zero is {fmt_pct(flat_mae)}. "
        f"TimesFM error is {relation} than the calendar mean. "
        f"The calendar mean uses only months before 2020. "
        f"TimesFM sees every completed month before the month it forecasts, including holdout months already printed. "
        f"The comparison uses the same holdout months and the same absolute error. "
        f"TimesFM does not choose the rule."
    )


def main() -> None:
    try:
        import timesfm  # type: ignore
    except Exception as error:  # noqa: BLE001
        print(f"TimesFM not installed ({error}). No experimental file written.")
        return
    if not hasattr(timesfm, "TimesFM3Forecaster"):
        print("TimesFM imported, and TimesFM3Forecaster is absent. No file written.")
        return

    panel = rwtc_month_panel()
    if len(panel) < 12:
        print("Holdout panel is shorter than 12 months. No file written.")
        return

    print(f"Loading {MODEL_ID} on CPU.")
    model = timesfm.TimesFM3Forecaster.from_pretrained(
        MODEL_ID,
        device="cpu",
        per_core_batch_size=1,
    )
    forecasts: list[float] = []
    for index, row in enumerate(panel):
        context = np.asarray(row["history"], dtype=np.float64)
        if context.size < 24 or not np.isfinite(context).all():
            print(f"Bad context for {row['year']}-{row['month']:02d}. No file written.")
            return
        output = model.predict(
            context=context,
            horizon=1,
            make_positive=False,
            use_symmetric_averaging=False,
            use_znorm=False,
        )
        point = np.asarray(output.forecast, dtype=np.float64).reshape(-1)
        if point.size < 1 or not np.isfinite(point[0]):
            print(f"Non-finite forecast at {row['year']}-{row['month']:02d}. No file written.")
            return
        forecasts.append(float(point[0]))
        if index == 0 or (index + 1) % 20 == 0 or index + 1 == len(panel):
            print(f"forecast {index + 1}/{len(panel)}")

    seasonal_errors = [row["realized"] - row["seasonal"] for row in panel]
    flat_errors = [row["realized"] - 0.0 for row in panel]
    timesfm_errors = [row["realized"] - pred for row, pred in zip(panel, forecasts)]
    seasonal_mae = mae(seasonal_errors)
    flat_mae = mae(flat_errors)
    timesfm_mae = mae(timesfm_errors)
    if seasonal_mae is None or flat_mae is None or timesfm_mae is None:
        print("MAE was empty. No file written.")
        return

    payload = {
        "model": MODEL_ID,
        "package": f"timesfm=={version('timesfm')}",
        "device": "cpu",
        "point": "median quantile",
        "horizon_months": 1,
        "make_positive": False,
        "context": "every completed month strictly before the target month",
        "holdout_start": "2020-01-01",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "n": len(panel),
        "seasonal_mae": seasonal_mae,
        "flat_mae": flat_mae,
        "timesfm_mae": timesfm_mae,
        "summary": summary(len(panel), timesfm_mae, seasonal_mae, flat_mae),
        "months": [
            {
                "month": f"{row['year']}-{row['month']:02d}",
                "realized": row["realized"],
                "seasonal": row["seasonal"],
                "timesfm": pred,
            }
            for row, pred in zip(panel, forecasts)
        ],
    }
    if "\u2014" in payload["summary"] or "\u2013" in payload["summary"]:
        print("Summary contains a dash that the repo forbids. No file written.")
        return
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(payload["summary"])
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
