# Methodology

The split is fixed in `scripts/studies.py`.

- Train: observations with date before 2020-01-01.
- Holdout: observations with date on or after 2020-01-01.
- Thresholds, percentiles, medians, and month means that a rule needs are computed on the train window only, then applied to the holdout unchanged.

A return is the log change between two published prints. The later print has to fall within 5 calendar days of the earlier one. A longer hole is dropped and counted. The hole is not filled.

Weekly stock changes are kept only when the two week-ending dates are 7 days apart.

The EIA week ends Friday. The release this study uses is the Wednesday five days later. The price reaction is the log change from the last WTI print strictly before that Wednesday to the print on that Wednesday. If Wednesday has no print, the week is skipped. Holiday releases that moved to Thursday are not reassigned. The skip count is part of the result.

Five-print returns step forward five published daily prints, not five calendar days.

One question is declared for each study before the holdout is scored. The page prints the train number and the holdout number. If the holdout does not carry the train sign, the prose says the holdout failed. No second threshold is tried.

The forecast study scores a seasonal naive (train mean for that calendar month) against a flat forecast of zero monthly log return. Mean absolute error on the holdout decides it. TimesFM 3.0, when `data/timesfm.json` is present, is a one-month median on the expanding history. It is labeled experimental and is not used to pick a rule.

Derived metrics live in `scripts/metrics.py`. The bars are fixed there:

- `INV_SURPRISE`: holdout correlation of the mean-baseline stock surprise with the Wednesday RWTC return is negative.
- `CUSHING_COVER`: the gap in five-print RWTC returns, low cover versus the rest, keeps its sign. Low cover is below the train 20th percentile.
- `CURVE_Z`: the gap between z above 1 and z below -1 keeps its sign.
- `COT_Z`: the gap between z above 1.5 and the rest keeps its sign.
- `CRACK_GAP`: the correlation with the next five-print RWTC return keeps its sign.
- `RV20`: holdout mean absolute five-print return is larger when realized vol is at or above the train 80th percentile. Implied vol is not in the file.
- EIA-day profile: Spearman correlation of the four surprise-bin means is positive.
- `SEAS_STOCK`: the correlation of the seasonal stock deviation with the Wednesday return keeps its sign.
- `UTIL_DEV`: holdout mean absolute Wednesday return is larger on utilization anomalies.
- `SPR_FLOW`: holdout correlation of the weekly SPR change with the Wednesday return is negative.

A held verdict is that bar and nothing else. The prose prints the train number and the holdout number.
