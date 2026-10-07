# Provenance

Retrieval dates live on each series file in `data/series/` after ingest. This note says what is allowed to be stored.

## Stored here

US government works. Public domain. The code around them is MIT. Republishing the figures is fine. Keep the series key and the retrieval date with them.

| Archive | What | File |
| --- | --- | --- |
| EIA | Cushing WTI spot `RWTC`, dollars per barrel, daily | `hist_xls/RWTCd.xls` |
| EIA | Europe Brent spot `RBRTE`, dollars per barrel, daily | `hist_xls/RBRTEd.xls` |
| EIA | NYMEX crude futures contracts 1 to 4, `RCLC1` to `RCLC4`, daily | `hist_xls/RCLC{1-4}d.xls` |
| EIA | NY Harbor No. 2 heating oil futures contract 1, dollars per gallon | `hist_xls/EER_EPD2F_PE1_Y35NY_DPGd.xls` |
| EIA | NY Harbor RBOB regular gasoline futures contract 1, dollars per gallon | `hist_xls/EER_EPMRR_PE1_Y35NY_DPGd.xls` |
| EIA | NY Harbor conventional gasoline regular spot, dollars per gallon | `hist_xls/EER_EPMRU_PF4_Y35NY_DPGd.xls` |
| EIA | NY Harbor No. 2 heating oil spot, dollars per gallon | `hist_xls/EER_EPD2F_PF4_Y35NY_DPGd.xls` |
| EIA | Weekly crude stocks excluding SPR `WCESTUS1`, thousand barrels | `hist_xls/WCESTUS1w.xls` |
| EIA | Weekly total crude stocks `WCRSTUS1`, thousand barrels | `hist_xls/WCRSTUS1w.xls` |
| EIA | Weekly Cushing stocks excluding SPR, thousand barrels | `hist_xls/W_EPC0_SAX_YCUOK_MBBLw.xls` |
| EIA | Weekly SPR `WCSSTUS1`, thousand barrels | `hist_xls/WCSSTUS1w.xls` |
| EIA | Weekly field production `WCRFPUS2`, thousand barrels per day | `hist_xls/WCRFPUS2w.xls` |
| EIA | Weekly refiner net inputs of crude `WCRRIUS2`, thousand barrels per day | `hist_xls/WCRRIUS2w.xls` |
| EIA | Weekly crude imports `WCRIMUS2` and exports `WCREXUS2`, thousand barrels per day | matching `hist_xls` files |
| EIA | Weekly refinery utilization `WPULEUS3`, percent | `hist_xls/WPULEUS3w.xls` |
| EIA | Weekly distillate stocks `WDISTUS1`, gasoline stocks, finished gasoline product supplied | matching `hist_xls` files |
| FRED | Broad dollar `DTWEXBGS`, 10-year `DGS10`, 2-year `DGS2` | `fredgraph.csv` |
| CFTC | Disaggregated futures, WTI-PHYSICAL `067651` and Brent last day `06765T` | annual `fut_disagg_txt_YEAR.zip` from 2010, plus current `c_disagg.txt` |

FRED `DCOILWTICO` and `DCOILBRENTEU` are the EIA spot series republished by the St. Louis Fed. They are not a second copy in the archive. `scripts/verify.py` uses them as a check: on dates both files print, the values have to match.

EIA prints a release date inside each workbook. Ingest stores that string.

CFTC rows are filtered to two contract codes. The rest of the combined report is not mirrored. Matching is by code, because the market name on `067651` has changed. The stable annual zip `fut_disagg_txt_YEAR.zip` returned 404 for 2006 through 2009 on the retrieval that built this snapshot, so those years are not in the file. The gap is recorded on the series as `history_gaps`.

## Calculated here

These are arithmetic on stored points. They are labeled `derived`. A date is omitted when any input is missing. Nothing is interpolated.

- `CL1_MINUS_CL4`: `RCLC1` minus `RCLC4`, dollars per barrel. Positive means the front contract is above the fourth.
- `CRACK_321`: `((2 * RBOB_F1 + HO_F1) / 3) * 42 - RCLC1`. Gasoline and heating oil are dollars per gallon. Times 42 converts a gallon quote to a barrel quote.
- `DGS10_MINUS_DGS2`: `DGS10` minus `DGS2`, percentage points.
- Managed money net: long minus short, contracts. Spreads are not folded in. The field says so.
- `INV_SURPRISE`, `CUSHING_COVER`, `CURVE_Z`, `COT_Z`, `COT_PCT`, `CRACK_GAP`, `RV20`, `SEAS_STOCK`, `UTIL_DEV`, `SPR_FLOW`: formulas and holdout bars are in `scripts/metrics.py` and on the page. `RV20` is realized volatility. Implied volatility is not stored.

## Not stored

| Source | Why it is a link |
| --- | --- |
| OPEC Monthly Oil Market Report | OPEC copyright. Headline figures are cited from the report page, not copied into `data/`. |
| IEA oil pages | IEA copyright. Same treatment. |
| Baker Hughes rig count | Baker Hughes publishes the count for readers of its site. The terms do not grant a clean right to mirror the workbook in a public git repo. The source page is linked from the site. |
| CME, ICE, and other live or delayed futures curves | Exchange market data is licensed. EIA's four contract months are the curve this archive is allowed to keep. A full 36-month board is not here. |
| CFTC Traders in Financial Futures | TFF covers rates, FX, and equity index futures. CL and Brent are in the disaggregated commodity file, which is what we store. |
| Analyst surprise surveys | Paid. The inventory study uses the prior 52 published weekly changes as the baseline and names that baseline. It is not a consensus surprise. |

## TimesFM

`scripts/timesfm_study.py` runs the open TimesFM 3.0 checkpoint `google/timesfm-3.0-pytorch` on CPU. The weights are downloaded at runtime from the public model host and are not committed. The script writes `data/timesfm.json` with the one-month median on each holdout month. If the package or the checkpoint is missing, it writes nothing. The seasonal-naive versus flat-forecast comparison is still the result the holdout is judged on.
