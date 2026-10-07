"use client";

import { useMemo, useState } from "react";
import { evaluateFormula } from "@/lib/formula.mjs";
import type { BookFile } from "@/lib/types";

type Extra = { key: string; formula: string };
type Regime = "all" | "backwardation" | "contango" | "extreme";

export function SheetGrid({
  book,
  start,
  end,
  regime,
  focus,
  curveDates,
  curveValues,
}: {
  book: BookFile;
  start: string;
  end: string;
  regime: Regime;
  focus: string;
  curveDates: string[];
  curveValues: Map<string, number>;
}) {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" }>({ key: "date", dir: "desc" });
  const [page, setPage] = useState(0);
  const [formula, setFormula] = useState("RWTC-RBRTE");
  const [extras, setExtras] = useState<Extra[]>([]);
  const [formulaError, setFormulaError] = useState("");

  const columns = useMemo(() => {
    const added = extras.map((extra) => ({
      key: extra.key,
      label: extra.key,
      unit: "formula",
      derived: true,
      formula: extra.formula,
      source: "Derived",
      source_url: "",
      retrieved_at: "",
      z: false,
    }));
    return [...book.columns, ...added];
  }, [book.columns, extras]);

  const prepared = useMemo(() => {
    return book.rows.map((row, index) => {
      const record: Record<string, string> = {};
      book.columns.forEach((column, columnIndex) => {
        record[column.key] = row[columnIndex] ?? "";
      });
      const prevRecord: Record<string, string> = {};
      const prev = index > 0 ? book.rows[index - 1] : [];
      book.columns.forEach((column, columnIndex) => {
        prevRecord[column.key] = prev[columnIndex] ?? "";
      });
      const extraValues = extras.map((extra) => {
        try {
          return evaluateFormula(extra.formula, record, prevRecord);
        } catch {
          return "";
        }
      });
      const cells = [...row, ...extraValues];
      const z = [...(book.z[index] ?? []), ...extras.map(() => null)];
      return { cells, z, date: row[0] ?? "" };
    });
  }, [book, extras]);

  const filtered = useMemo(() => {
    const focusIndex = columns.findIndex((column) => column.key === focus);
    return prepared.filter((item) => {
      if (start && item.date < start) return false;
      if (end && item.date > end) return false;
      if (regime === "backwardation" || regime === "contango") {
        const spread = spreadOn(item.date, curveDates, curveValues);
        if (spread == null) return false;
        if (regime === "backwardation" && !(spread > 0)) return false;
        if (regime === "contango" && !(spread < 0)) return false;
      }
      if (regime === "extreme") {
        const zed = focusIndex >= 0 ? item.z[focusIndex] : null;
        if (zed == null || Math.abs(Number(zed)) <= 4) return false;
      }
      return columns.every((column, index) => {
        const filter = (filters[column.key] ?? "").trim();
        if (!filter) return true;
        const cell = item.cells[index] ?? "";
        if (filter.startsWith(">") || filter.startsWith("<")) {
          const limit = Number(filter.slice(1));
          const value = Number(cell);
          if (!Number.isFinite(limit) || !Number.isFinite(value)) return false;
          return filter.startsWith(">") ? value > limit : value < limit;
        }
        return cell.toLowerCase().includes(filter.toLowerCase());
      });
    });
  }, [prepared, start, end, regime, focus, columns, filters, curveDates, curveValues]);

  const sorted = useMemo(() => {
    const index = Math.max(0, columns.findIndex((column) => column.key === sort.key));
    const copy = [...filtered];
    copy.sort((left, right) => {
      const a = left.cells[index] ?? "";
      const b = right.cells[index] ?? "";
      const an = Number(a);
      const bn = Number(b);
      let cmp = 0;
      if (a !== "" && b !== "" && Number.isFinite(an) && Number.isFinite(bn)) cmp = an - bn;
      else cmp = a < b ? -1 : a > b ? 1 : 0;
      return sort.dir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [filtered, columns, sort]);

  const pageSize = 80;
  const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, pages - 1);
  const view = sorted.slice(safePage * pageSize, safePage * pageSize + pageSize);
  const extremes = countExtremes(sorted, columns, focus);

  function addFormula() {
    const sample = prepared[prepared.length - 1];
    const record = objectFrom(book, sample);
    const prev = objectFrom(book, prepared[prepared.length - 2]);
    try {
      evaluateFormula(formula, record, prev);
      const key = `F${extras.length + 1}`;
      setExtras((current) => [...current, { key, formula }]);
      setFormulaError("");
      setPage(0);
    } catch (error) {
      setFormulaError(error instanceof Error ? error.message : "Formula failed.");
    }
  }

  async function download(kind: "csv" | "json" | "parquet") {
    const headers = columns.map((column) => column.key);
    if (kind === "json") {
      const payload = sorted.map((item) => Object.fromEntries(headers.map((key, index) => [key, item.cells[index] ?? ""])));
      saveBlob(new Blob([JSON.stringify(payload)], { type: "application/json" }), `${book.id}-view.json`);
      return;
    }
    if (kind === "csv") {
      const lines = [headers.join(",")];
      for (const item of sorted) {
        lines.push(item.cells.map((cell) => csv(cell ?? "")).join(","));
      }
      saveBlob(new Blob([lines.join("\n")], { type: "text/csv" }), `${book.id}-view.csv`);
      return;
    }
    const { parquetWriteBuffer } = await import("hyparquet-writer");
    const buffer = parquetWriteBuffer({
      codec: "UNCOMPRESSED",
      columnData: headers.map((key, index) => {
        const values = sorted.map((item) => item.cells[index] ?? "");
        if (key === "date") return { name: key, data: values, type: "STRING" as const };
        return {
          name: key,
          data: values.map((value) => (value === "" ? null : Number(value))),
          type: "DOUBLE" as const,
        };
      }),
    });
    saveBlob(new Blob([buffer], { type: "application/vnd.apache.parquet" }), `${book.id}-view.parquet`);
  }

  return (
    <div className="sheet">
      <div className="formula-bar">
        <label>
          <span>Formula</span>
          <input
            value={formula}
            onChange={(event) => setFormula(event.target.value)}
            aria-label="Formula"
            spellCheck={false}
          />
        </label>
        <button type="button" onClick={addFormula}>
          Add column
        </button>
        <p>
          LAG, LOG, and ABS. A blank input stays blank. The column is calculated in the browser and labeled derived.
          {formulaError ? ` ${formulaError}` : ""}
        </p>
      </div>
      <div className="toolbar">
        <span>
          {sorted.length} rows in the window. {extremes} with |z| above 4 on {focus}. Page {safePage + 1} of {pages}.
        </span>
        <div className="pager">
          <button type="button" onClick={() => setPage(Math.max(0, safePage - 1))} disabled={safePage === 0}>
            Prev
          </button>
          <button type="button" onClick={() => setPage(Math.min(pages - 1, safePage + 1))} disabled={safePage >= pages - 1}>
            Next
          </button>
          <button type="button" onClick={() => download("csv")}>CSV</button>
          <button type="button" onClick={() => download("json")}>JSON</button>
          <button type="button" onClick={() => download("parquet")}>Parquet</button>
        </div>
      </div>
      <p className="meta-line">
        Dither marks |z| at or above 2. A black cell is |z| above 4, the same cutoff as the anomaly study on RWTC returns.
        Full files, unfiltered, sit at /downloads/{book.id}.csv and /downloads/{book.id}.parquet.
      </p>
      <div className="sheet-scroll">
        <table>
          <caption>{book.name}</caption>
          <thead>
            <tr>
              <th className="row-num">#</th>
              {columns.map((column) => (
                <th key={column.key} className={column.key === focus ? "col-focus" : undefined}>
                  <button
                    type="button"
                    onClick={() => {
                      setSort((current) =>
                        current.key === column.key
                          ? { key: column.key, dir: current.dir === "desc" ? "asc" : "desc" }
                          : { key: column.key, dir: "desc" },
                      );
                      setPage(0);
                    }}
                    title={columnNote(column)}
                  >
                    {column.label}
                    {column.derived ? " · d" : ""}
                    {sort.key === column.key ? (sort.dir === "asc" ? " ↑" : " ↓") : ""}
                  </button>
                </th>
              ))}
            </tr>
            <tr>
              <th className="row-num" />
              {columns.map((column) => (
                <th key={`${column.key}-filter`}>
                  <input
                    value={filters[column.key] ?? ""}
                    aria-label={`Filter ${column.label}`}
                    placeholder="> or text"
                    onChange={(event) => {
                      setFilters((current) => ({ ...current, [column.key]: event.target.value }));
                      setPage(0);
                    }}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((item, rowIndex) => (
              <tr key={`${item.date}-${rowIndex}`}>
                <td className="row-num">{safePage * pageSize + rowIndex + 1}</td>
                {item.cells.map((cell, index) => {
                  const zed = item.z[index];
                  const score = zed == null || zed === "" ? null : Number(zed);
                  const klass = [
                    columns[index]?.key === focus ? "col-focus" : "",
                    score != null && Math.abs(score) > 4 ? "cell-extreme" : "",
                    score != null && Math.abs(score) >= 2 && Math.abs(score) <= 4 ? "cell-outlier" : "",
                  ]
                    .filter(Boolean)
                    .join(" ");
                  return (
                    <td key={`${item.date}-${columns[index]?.key}`} className={klass || undefined} title={score == null ? undefined : `z ${zed}`}>
                      {cell}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function objectFrom(book: BookFile, item?: { cells: string[] }) {
  const record: Record<string, string> = {};
  book.columns.forEach((column, index) => {
    record[column.key] = item?.cells[index] ?? "";
  });
  return record;
}

function countExtremes(
  rows: { z: (string | null)[] }[],
  columns: { key: string }[],
  focus: string,
) {
  const index = columns.findIndex((column) => column.key === focus);
  if (index < 0) return 0;
  return rows.filter((row) => {
    const zed = row.z[index];
    return zed != null && Math.abs(Number(zed)) > 4;
  }).length;
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

function columnNote(column: BookFile["columns"][number]) {
  const source = column.source ? `${column.source}. ` : "";
  const when = column.retrieved_at ? `Retrieved ${column.retrieved_at.slice(0, 10)}. ` : "";
  return `${source}${when}${column.unit}. ${column.formula}`;
}

function csv(value: string) {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
