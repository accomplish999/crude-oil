import type { Catalog, CatalogEntry } from "@/lib/types";

function series(catalog: Catalog, id: string): CatalogEntry {
  const found = catalog.series.find((item) => item.id === id);
  if (!found) {
    return {
      id,
      name: id,
      unit: "",
      frequency: "",
      group: "",
      source: "",
      source_key: "",
      source_url: "",
      download_url: "",
      license: "",
      retrieved_at: catalog.retrieved_at,
      release_date: "",
      derived: false,
      method: "",
      inputs: [],
      fields: [],
      count: 0,
      start: "",
      end: "",
      last_value: "",
      last_field: "",
    };
  }
  return found;
}

function print(item: CatalogEntry) {
  return `${item.end} at ${item.last_value} ${item.unit}`.trim();
}

export function explainers(catalog: Catalog) {
  const wti = series(catalog, "RWTC");
  const brent = series(catalog, "RBRTE");
  const cushing = series(catalog, "CUSHING");
  const cover = series(catalog, "CUSHING_COVER");
  const curve = series(catalog, "CL1_MINUS_CL4");
  const crack = series(catalog, "CRACK_321");
  return [
    {
      id: "wti-brent",
      title: "WTI and Brent",
      body: [
        `WTI on this page is EIA RWTC, the Cushing, Oklahoma spot, dollars per barrel. Last stored print: ${print(wti)}. Source file RWTCd.xls, retrieved ${wti.retrieved_at.slice(0, 10)}.`,
        `Brent is EIA RBRTE, the Europe spot. Last stored print: ${print(brent)}. They are different barrels in different places. A day missing either print is left blank. The page does not fill a spread across that hole.`,
      ],
    },
    {
      id: "cushing",
      title: "Cushing",
      body: [
        `Cushing stocks are the EIA weekly series for Cushing, Oklahoma, excluding the SPR, thousand barrels. Stored id CUSHING. Last week: ${print(cushing)}.`,
        `Days of cover, CUSHING_COVER, divides that stock by the same Friday's refiner net inputs of crude, WCRRIUS2. Both are thousand barrels over thousand barrels per day, so the unit is days. Last derived print: ${print(cover)}. The column is marked derived. The holdout test is in the metrics table, and it does not get a new cutoff after the result.`,
      ],
    },
    {
      id: "contango",
      title: "Contango and backwardation",
      body: [
        `CL1_MINUS_CL4 is NYMEX contract 1 minus contract 4, on dates both EIA series print. Positive means the front is above the fourth. That is the backwardation side of this two-point curve. Negative is contango in the same two contracts. Last stored spread: ${print(curve)}.`,
        `EIA's futures history in this snapshot ends ${curve.end}. Spot RWTC continues after that. CURVE_Z is the spread minus its pre-2020 mean, divided by the pre-2020 standard deviation. Dates after the futures file are absent, not extrapolated.`,
      ],
    },
    {
      id: "cot",
      title: "Commitments of Traders",
      body: [
        "Managed money for WTI is CFTC disaggregated futures, contract code 067651. Brent last day is 06765T. Net is long minus short. Spreads are not folded into the net. COT_Z is that net divided by open interest, then scored against the pre-2020 mean and standard deviation. COT_PCT is the share of the pre-2020 prints at or below the current ratio.",
        "The annual history files for 2006 through 2009 were not on the CFTC server when this snapshot was built, so the stored report starts in 2010. Traders in Financial Futures does not list CL, and it is not copied here.",
      ],
    },
    {
      id: "cracks",
      title: "The 3-2-1 crack",
      body: [
        `The crack is ((2 * RBOB futures contract 1 + heating oil futures contract 1) / 3) * 42, minus NYMEX crude contract 1. Gasoline and heating oil are dollars per gallon. Times 42 puts a gallon quote on a barrel. Last stored crack: ${print(crack)}.`,
        "CRACK_GAP subtracts the median of cracks from before 2020. A date is dropped when any input is missing. Implied volatility is not in the free files, so there is no implied-versus-realized ratio. RV20 is the annualized standard deviation of 20 adjacent RWTC log returns, and the column says so.",
      ],
    },
    {
      id: "eia-report",
      title: "The EIA week",
      body: [
        "The weekly petroleum file ends on Friday. The studies treat the nominal release as the Wednesday five days later. The price reaction is the log change from the last RWTC print before that Wednesday to the print on that Wednesday.",
        "If Wednesday has no RWTC print, the week is skipped and counted. A holiday release that moved to Thursday is not reassigned. The inventory surprise is the weekly stock change minus a trailing baseline from the prior 52 kept weeks. It is not an analyst survey.",
      ],
    },
  ];
}

export function faq(catalog: Catalog) {
  const wti = series(catalog, "RWTC");
  return [
    {
      q: "What price is WTI here?",
      a: `WTI is EIA RWTC, Cushing spot, dollars per barrel. The last stored print is ${wti.last_value} on ${wti.end}, retrieved ${wti.retrieved_at.slice(0, 10)}.`,
    },
    {
      q: "How is Brent different from WTI in this archive?",
      a: "Brent is EIA RBRTE, the Europe spot. It is a different barrel and a different file. The two series are not averaged, and a missing day stays blank.",
    },
    {
      q: "What does contango mean on this page?",
      a: "Contango here means CL1_MINUS_CL4 is negative: NYMEX contract 4 is above contract 1. Backwardation means the front is above the fourth. The futures file ends before the spot file.",
    },
    {
      q: "What is the COT figure?",
      a: "It is the CFTC disaggregated futures report for codes 067651 and 06765T. Managed-money net is long minus short, without spreads. The z-score and the percentile use the pre-2020 distribution only.",
    },
    {
      q: "How is the crack calculated?",
      a: "((2 * RBOB futures + heating oil futures) / 3) * 42, minus NYMEX crude contract 1. The 42 converts a gallon quote to a barrel quote. Missing inputs are omitted.",
    },
    {
      q: "When does the EIA week hit the price?",
      a: "The week ends Friday. The nominal release in the studies is the Wednesday five days later. Weeks with no Wednesday RWTC print are skipped. Thursday holiday releases are not moved.",
    },
    {
      q: "Does a held study mean there is a trade?",
      a: "No. Held means the precommitted bar was met on the holdout that starts 1 Jan 2020. Some held results are sign tests on thin numbers. Failed means the bar was missed. Read the number on the row.",
    },
    {
      q: "Is this financial advice?",
      a: "No. Past prices do not predict future prices. A futures contract can wipe out the account that trades it.",
    },
  ];
}

export function structuredData(catalog: Catalog, entries: { q: string; a: string }[], site: string) {
  const wti = series(catalog, "RWTC");
  const downloads = ["prices", "weekly", "positions"].flatMap((id) => [
    {
      "@type": "DataDownload",
      encodingFormat: "text/csv",
      contentUrl: `${site}/downloads/${id}.csv`,
    },
    {
      "@type": "DataDownload",
      encodingFormat: "application/vnd.apache.parquet",
      contentUrl: `${site}/downloads/${id}.parquet`,
    },
  ]);
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Dataset",
        name: "Crude oil archive",
        description:
          "EIA spot and weekly petroleum series, the four NYMEX crude contracts EIA publishes, CFTC managed money for 067651 and 06765T, and derived columns with formulas. US government series are public domain. Derived columns are arithmetic on those series.",
        url: `${site}/`,
        dateModified: catalog.retrieved_at,
        license: "https://github.com/accomplish999/crude-oil/blob/main/LICENSE",
        creator: {
          "@type": "Organization",
          name: "crude oil contributors",
          url: "https://github.com/accomplish999/crude-oil",
        },
        keywords: ["WTI", "Brent", "Cushing", "CFTC", "crack spread", "EIA", "contango"],
        temporalCoverage: wti.start && wti.end ? `${wti.start}/${wti.end}` : undefined,
        distribution: downloads,
      },
      {
        "@type": "FAQPage",
        mainEntity: entries.map((item) => ({
          "@type": "Question",
          name: item.q,
          acceptedAnswer: { "@type": "Answer", text: item.a },
        })),
      },
    ],
  };
}
