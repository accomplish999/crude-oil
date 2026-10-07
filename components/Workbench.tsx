"use client";

import { useEffect, useMemo, useState } from "react";
import { DitherChart } from "@/components/DitherChart";
import { RiskTool } from "@/components/RiskTool";
import { SheetGrid } from "@/components/SheetGrid";
import type { BookFile } from "@/lib/types";

const base = (process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(/\/$/, "");

type Regime = "all" | "backwardation" | "contango" | "extreme";

export function Workbench({
  defaultStart,
  curveEnd,
  spotEnd,
}: {
  defaultStart: string;
  curveEnd: string;
  spotEnd: string;
}) {
  const [books, setBooks] = useState<Record<string, BookFile>>({});
  const [error, setError] = useState("");
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState("");
  const [seriesId, setSeriesId] = useState("RWTC");
  const [regime, setRegime] = useState<Regime>("all");
  const [bookId, setBookId] = useState("prices");

  useEffect(() => {
    let cancel = false;
    Promise.all(
      ["prices", "weekly", "positions"].map((id) =>
        fetch(`${base}/api/book/${id}/`).then((response) => {
          if (!response.ok) throw new Error(id);
          return response.json() as Promise<BookFile>;
        }),
      ),
    )
      .then((loaded) => {
        if (cancel) return;
        const next: Record<string, BookFile> = {};
        for (const book of loaded) next[book.id] = book;
        setBooks(next);
      })
      .catch(() => {
        if (!cancel) setError("The sheet failed to load.");
      });
    return () => {
      cancel = true;
    };
  }, []);

  const options = useMemo(() => {
    const seen = new Set<string>();
    const list: { key: string; label: string; book: string }[] = [];
    for (const id of ["prices", "weekly", "positions"]) {
      for (const column of books[id]?.columns ?? []) {
        if (column.key === "date" || seen.has(column.key)) continue;
        seen.add(column.key);
        list.push({ key: column.key, label: `${column.label} (${id})`, book: id });
      }
    }
    return list;
  }, [books]);

  const book = books[bookId] ?? null;
  const prices = books.prices ?? null;
  const chartBookId = options.find((item) => item.key === seriesId)?.book ?? "prices";
  const chartBook = books[chartBookId] ?? null;
  const curve = useMemo(() => buildCurve(prices), [prices]);
  const chart = useMemo(() => {
    if (!chartBook) return null;
    const index = chartBook.columns.findIndex((column) => column.key === seriesId);
    if (index < 0) return null;
    const points = chartBook.rows
      .map((row, rowIndex) => ({
        date: row[0],
        value: row[index],
        z: chartBook.z[rowIndex]?.[index] ?? null,
      }))
      .filter((point) => point.value && (!start || point.date >= start) && (!end || point.date <= end))
      .filter((point) => keepRegime(point.date, point.z, regime, curve));
    if (!points.length) return { stat: "n/a", last: "", points: [] as { x: number; y: number }[], lines: [] as { name: string; values: { x: number; y: number }[] }[] };
    const last = points[points.length - 1];
    const values = points.map((point) => ({ x: Date.parse(`${point.date}T00:00:00Z`), y: Number(point.value) }));
    return {
      stat: last.value,
      last: last.date,
      points: values,
      lines: [{ name: seriesId, values }],
    };
  }, [chartBook, seriesId, start, end, regime, curve]);

  const summary = useMemo(() => {
    if (!chart || !chartBook) return null;
    const index = chartBook.columns.findIndex((column) => column.key === seriesId);
    const values = chart.points.map((point) => point.y);
    if (!values.length || index < 0) return null;
    const extreme = chartBook.rows.filter((row, rowIndex) => {
      if (start && row[0] < start) return false;
      if (end && row[0] > end) return false;
      const zed = chartBook.z[rowIndex]?.[index];
      return zed != null && Math.abs(Number(zed)) > 4 && keepRegime(row[0], zed, regime, curve);
    }).length;
    return {
      n: values.length,
      min: Math.min(...values),
      max: Math.max(...values),
      extreme,
    };
  }, [chartBook, chart, seriesId, start, end, regime, curve]);

  return (
    <>
      <div className="filter-bar">
        <label>
          <span>From</span>
          <input value={start} onChange={(event) => setStart(event.target.value)} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          <span>To</span>
          <input value={end} onChange={(event) => setEnd(event.target.value)} placeholder="YYYY-MM-DD" />
        </label>
        <label>
          <span>Series</span>
          <select
            value={seriesId}
            onChange={(event) => {
              const next = event.target.value;
              setSeriesId(next);
              const home = options.find((item) => item.key === next);
              if (home) setBookId(home.book);
            }}
          >
            {options.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Regime</span>
          <select value={regime} onChange={(event) => setRegime(event.target.value as Regime)}>
            <option value="all">All prints</option>
            <option value="backwardation">CL1 above CL4</option>
            <option value="contango">CL1 below CL4</option>
            <option value="extreme">|z| above 4</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            setStart("");
            setEnd("");
            setRegime("all");
          }}
        >
          All dates
        </button>
      </div>
      <p className="meta-line">
        The date, the series, and the regime cut the chart and the sheet together. Study verdicts stay on the split in the code: train before 1 Jan 2020, holdout from that day.
        {curveEnd && spotEnd && curveEnd < spotEnd
          ? ` CL1 minus CL4 ends ${curveEnd}. Spot RWTC runs through ${spotEnd}. A curve regime drops dates after the futures file.`
          : ""}
      </p>
      {error ? <p>{error}</p> : null}

      <section className="panel" id="charts">
        <h2>{seriesId} in the window</h2>
        {!chartBook && !error ? (
          <p>Loading the chart.</p>
        ) : chart && chart.points.length > 1 ? (
          <DitherChart
            stat={chart.stat}
            statLabel={`${seriesId} ${chart.last}. ${regime === "all" ? "All regimes in the window." : `Regime: ${regime}.`}`}
            lines={chart.lines}
          />
        ) : (
          <p>Not enough prints in this window to draw the line.</p>
        )}
        {summary ? (
          <div className="table-wrap">
            <table>
              <caption>Window for {seriesId}</caption>
              <thead>
                <tr>
                  <th>Prints</th>
                  <th>Min</th>
                  <th>Max</th>
                  <th>Last</th>
                  <th>|z| above 4</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{summary.n}</td>
                  <td>{trim(summary.min)}</td>
                  <td>{trim(summary.max)}</td>
                  <td>{chart?.stat}</td>
                  <td>{summary.extreme}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="panel" id="sheet">
        <h2>Sheet</h2>
        <div className="pager book-tabs">
          {["prices", "weekly", "positions"].map((id) => (
            <button key={id} type="button" onClick={() => setBookId(id)} aria-pressed={bookId === id}>
              {id}
            </button>
          ))}
        </div>
        {book ? (
          <SheetGrid
            book={book}
            start={start}
            end={end}
            regime={regime}
            focus={seriesId}
            curveDates={curve.dates}
            curveValues={curve.values}
          />
        ) : (
          <p>Loading the sheet.</p>
        )}
      </section>

      <RiskTool book={prices} start={start} end={end} />
    </>
  );
}

function buildCurve(book: BookFile | null) {
  const dates: string[] = [];
  const values = new Map<string, number>();
  if (!book) return { dates, values };
  const index = book.columns.findIndex((column) => column.key === "CL1_MINUS_CL4");
  if (index < 0) return { dates, values };
  for (const row of book.rows) {
    if (!row[index]) continue;
    dates.push(row[0]);
    values.set(row[0], Number(row[index]));
  }
  return { dates, values };
}

function keepRegime(date: string, z: string | null, regime: Regime, curve: { dates: string[]; values: Map<string, number> }) {
  if (regime === "all") return true;
  if (regime === "extreme") return z != null && Math.abs(Number(z)) > 4;
  const spread = spreadOn(date, curve.dates, curve.values);
  if (spread == null) return false;
  return regime === "backwardation" ? spread > 0 : spread < 0;
}

function spreadOn(day: string, dates: string[], values: Map<string, number>) {
  let lo = 0;
  let hi = dates.length - 1;
  let found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (dates[mid] <= day) {
      found = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  if (found < 0) return null;
  return values.get(dates[found]) ?? null;
}

function trim(value: number) {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
}
