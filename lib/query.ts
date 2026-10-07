import type { CitedRow, SeriesFile, Study, ToolCall } from "@/lib/types";

const MAX_ROWS = 40;

export function defaultField(series: SeriesFile): string {
  if (series.fields.some((field) => field.key === "value")) return "value";
  if (series.fields.some((field) => field.key === "mm_net")) return "mm_net";
  return series.fields[0]?.key ?? "value";
}

export function cite(
  series: SeriesFile,
  field: string,
  row: { date: string; [key: string]: string },
): CitedRow {
  return {
    series_id: series.id,
    field,
    date: row.date,
    value: row[field],
    unit: series.fields.find((item) => item.key === field)?.unit || series.unit,
    source: series.source,
    source_url: series.source_url,
    retrieved_at: series.retrieved_at,
  };
}

export function latest(series: SeriesFile, field = defaultField(series)): ToolCall {
  const row = [...series.observations].reverse().find((item) => item[field]);
  return {
    name: "latest",
    args: { series_id: series.id, field },
    rows: row ? [cite(series, field, row)] : [],
    note: row
      ? `${series.id} ${field} ${row.date} = ${row[field]}`
      : `${series.id} has no ${field}`,
  };
}

export function range(
  series: SeriesFile,
  start: string,
  end: string,
  field = defaultField(series),
  limit = MAX_ROWS,
): ToolCall {
  const cap = Math.min(Math.max(limit, 1), MAX_ROWS);
  const rows = series.observations.filter((row) => {
    if (!row[field]) return false;
    if (start && row.date < start) return false;
    if (end && row.date > end) return false;
    return true;
  });
  const sliced = rows.slice(-cap);
  return {
    name: "range",
    args: { series_id: series.id, field, start, end, limit: String(cap) },
    rows: sliced.map((row) => cite(series, field, row)),
    note: `${series.id} ${field}: ${rows.length} rows in range, showing ${sliced.length}. Source ${series.source}, retrieved ${series.retrieved_at}.`,
  };
}

export function largeMoves(series: SeriesFile, count = 8): ToolCall {
  const field = defaultField(series);
  const rows = series.observations.filter((row) => row[field]);
  const moves: { abs: number; row: CitedRow; prev: CitedRow }[] = [];
  for (let index = 1; index < rows.length; index += 1) {
    const prev = Number(rows[index - 1][field]);
    const next = Number(rows[index][field]);
    if (!Number.isFinite(prev) || !Number.isFinite(next) || prev === 0) continue;
    const gap = dateGap(rows[index - 1].date, rows[index].date);
    if (gap < 1 || gap > 5) continue;
    moves.push({
      abs: Math.abs(Math.log(next / prev)),
      row: cite(series, field, rows[index]),
      prev: cite(series, field, rows[index - 1]),
    });
  }
  moves.sort((a, b) => b.abs - a.abs);
  const top = moves.slice(0, count);
  const cited = top.flatMap((move) => [move.prev, move.row]);
  return {
    name: "large_moves",
    args: { series_id: series.id, field, count: String(count) },
    rows: cited,
    note: `Largest adjacent log changes in ${series.id} where the prints are 1 to 5 calendar days apart. Each move is the prior print then the later print. Holes longer than 5 days are ignored.`,
  };
}

export function studyCall(study: Study): ToolCall {
  return {
    name: "study",
    args: { slug: study.slug },
    rows: [],
    note: `${study.index} ${study.title}: ${study.verdict}. ${study.verdict_line}`,
  };
}

function dateGap(start: string, end: string): number {
  const a = Date.parse(`${start}T00:00:00Z`);
  const b = Date.parse(`${end}T00:00:00Z`);
  return Math.round((b - a) / 86400000);
}

export function numbersIn(text: string): string[] {
  const found = text.match(/\d[\d,]*(?:\.\d+)?/g) ?? [];
  return found.map((item) => item.replace(/,/g, ""));
}

export function unverifiedNumbers(answer: string, evidence: string): string[] {
  const haystack = evidence.replace(/,/g, "");
  const suspects = numbersIn(answer).filter((item) => {
    const numeric = Number(item);
    if (!Number.isFinite(numeric)) return false;
    if (item.includes(".")) return true;
    return numeric >= 100;
  });
  return suspects.filter((item) => !haystack.includes(item));
}
