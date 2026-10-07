import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import type { Catalog, ChangelogEntry, MetricFile, SeriesFile, StudyFile } from "@/lib/types";

const root = process.cwd();

let seriesCache: Map<string, SeriesFile> | null = null;

export function readCatalog(): Catalog {
  const file = path.join(root, "data", "catalog.json");
  return JSON.parse(readFileSync(file, "utf8")) as Catalog;
}

export function readStudies(): StudyFile {
  const file = path.join(root, "data", "studies.json");
  return JSON.parse(readFileSync(file, "utf8")) as StudyFile;
}

export function readMetrics(): MetricFile {
  const file = path.join(root, "data", "metrics.json");
  return JSON.parse(readFileSync(file, "utf8")) as MetricFile;
}

export function readChangelog(): { entries: ChangelogEntry[] } {
  const file = path.join(root, "data", "changelog.json");
  return JSON.parse(readFileSync(file, "utf8")) as { entries: ChangelogEntry[] };
}

export function readSeries(id: string): SeriesFile | null {
  const all = loadSeries();
  return all.get(id) ?? null;
}

export function loadSeries(): Map<string, SeriesFile> {
  if (seriesCache) return seriesCache;
  const dir = path.join(root, "data", "series");
  const map = new Map<string, SeriesFile>();
  for (const name of readdirSync(dir)) {
    if (!name.endsWith(".json")) continue;
    const series = JSON.parse(
      readFileSync(path.join(dir, name), "utf8"),
    ) as SeriesFile;
    map.set(series.id, series);
  }
  seriesCache = map;
  return map;
}

export const siteUrl = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://accompli.sh/crude-oil"
).replace(/\/$/, "");

export const basePath = (process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(
  /\/$/,
  "",
);
