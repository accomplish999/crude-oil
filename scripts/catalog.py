"""Series this archive is allowed to store.

EIA and FRED files are US government work. CFTC disaggregated futures are too.
OPEC, IEA, Baker Hughes, and exchange quote feeds are intentionally absent.
"""

EIA_XLS = [
    {
        "id": "RWTC",
        "file": "RWTCd.xls",
        "frequency": "daily",
        "group": "price",
    },
    {
        "id": "RBRTE",
        "file": "RBRTEd.xls",
        "frequency": "daily",
        "group": "price",
    },
    {
        "id": "RCLC1",
        "file": "RCLC1d.xls",
        "frequency": "daily",
        "group": "curve",
    },
    {
        "id": "RCLC2",
        "file": "RCLC2d.xls",
        "frequency": "daily",
        "group": "curve",
    },
    {
        "id": "RCLC3",
        "file": "RCLC3d.xls",
        "frequency": "daily",
        "group": "curve",
    },
    {
        "id": "RCLC4",
        "file": "RCLC4d.xls",
        "frequency": "daily",
        "group": "curve",
    },
    {
        "id": "HO_F1",
        "file": "EER_EPD2F_PE1_Y35NY_DPGd.xls",
        "frequency": "daily",
        "group": "crack",
    },
    {
        "id": "RBOB_F1",
        "file": "EER_EPMRR_PE1_Y35NY_DPGd.xls",
        "frequency": "daily",
        "group": "crack",
    },
    {
        "id": "HO_SPOT",
        "file": "EER_EPD2F_PF4_Y35NY_DPGd.xls",
        "frequency": "daily",
        "group": "crack",
    },
    {
        "id": "GAS_SPOT",
        "file": "EER_EPMRU_PF4_Y35NY_DPGd.xls",
        "frequency": "daily",
        "group": "crack",
    },
    {
        "id": "WCESTUS1",
        "file": "WCESTUS1w.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "WCRSTUS1",
        "file": "WCRSTUS1w.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "CUSHING",
        "file": "W_EPC0_SAX_YCUOK_MBBLw.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "WCSSTUS1",
        "file": "WCSSTUS1w.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "WDISTUS1",
        "file": "WDISTUS1w.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "WGTSTUS1",
        "file": "WGTSTUS1w.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "WGIRIUS2",
        "file": "WGIRIUS2w.xls",
        "frequency": "weekly",
        "group": "stocks",
    },
    {
        "id": "WCRFPUS2",
        "file": "WCRFPUS2w.xls",
        "frequency": "weekly",
        "group": "balance",
    },
    {
        "id": "WCRRIUS2",
        "file": "WCRRIUS2w.xls",
        "frequency": "weekly",
        "group": "balance",
    },
    {
        "id": "WCRIMUS2",
        "file": "WCRIMUS2w.xls",
        "frequency": "weekly",
        "group": "balance",
    },
    {
        "id": "WCREXUS2",
        "file": "WCREXUS2w.xls",
        "frequency": "weekly",
        "group": "balance",
    },
    {
        "id": "WPULEUS3",
        "file": "WPULEUS3w.xls",
        "frequency": "weekly",
        "group": "balance",
    },
    {
        "id": "WGFUPUS2",
        "file": "WGFUPUS2w.xls",
        "frequency": "weekly",
        "group": "balance",
    },
]

FRED = [
    {
        "id": "DTWEXBGS",
        "frequency": "daily",
        "group": "macro",
        "name": "Nominal Broad US Dollar Index",
        "unit": "index, Jan 2006=100",
    },
    {
        "id": "DGS10",
        "frequency": "daily",
        "group": "macro",
        "name": "Market Yield on US Treasury Securities at 10-Year Constant Maturity",
        "unit": "percent",
    },
    {
        "id": "DGS2",
        "frequency": "daily",
        "group": "macro",
        "name": "Market Yield on US Treasury Securities at 2-Year Constant Maturity",
        "unit": "percent",
    },
]

# Republished EIA spots. Used only as a cross-check, never as a second archive copy.
FRED_CROSSCHECK = {
    "RWTC": "DCOILWTICO",
    "RBRTE": "DCOILBRENTEU",
}

CFTC_CODES = {
    "067651": {
        "id": "CFTC_CL",
        "name": "WTI-PHYSICAL, NYMEX, CFTC disaggregated futures",
    },
    "06765T": {
        "id": "CFTC_BRENT",
        "name": "Brent last day, NYMEX, CFTC disaggregated futures",
    },
}

# Annual zips before 2010 404 at the stable fut_disagg_txt_YEAR path.
CFTC_YEARS = list(range(2010, 2027))

HOLDOUT_START = "2020-01-01"
MAX_GAP_DAYS = 5
USER_AGENT = "crude-oil-archive/1.0 (public research; +https://github.com/accomplish999/crude-oil)"
