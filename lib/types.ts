export type Field = {
  key: string;
  name: string;
  unit: string;
  derived: boolean;
};

export type Observation = {
  date: string;
  [key: string]: string;
};

export type SeriesFile = {
  id: string;
  name: string;
  unit: string;
  frequency: string;
  group: string;
  source: string;
  source_key: string;
  source_url: string;
  download_url: string;
  license: string;
  retrieved_at: string;
  release_date: string;
  next_release?: string;
  derived: boolean;
  method: string;
  inputs: string[];
  fields: Field[];
  observations: Observation[];
  market_names?: string[];
};

export type CatalogEntry = {
  id: string;
  name: string;
  unit: string;
  frequency: string;
  group: string;
  source: string;
  source_key: string;
  source_url: string;
  download_url: string;
  license: string;
  retrieved_at: string;
  release_date: string;
  derived: boolean;
  method: string;
  inputs: string[];
  fields: Field[];
  count: number;
  start: string;
  end: string;
  last_value: string;
  last_field: string;
};

export type Catalog = {
  retrieved_at: string;
  series: CatalogEntry[];
};

export type StudyChart = {
  type: "bars";
  stat: string;
  stat_label: string;
  categories: string[];
  series: { name: string; values: number[] }[];
};

export type Study = {
  slug: string;
  index: string;
  title: string;
  kicker: string;
  question: string;
  verdict: "held" | "failed" | "flat";
  verdict_line: string;
  group?: "metric" | "study";
  formula?: string;
  chart: StudyChart;
  table: { caption: string; columns: string[]; rows: string[][] };
  cells: { label: string; body: string[] }[];
  stats: Record<string, number | null>;
};

export type StudyFile = {
  holdout_start: string;
  generated_from: string;
  studies: Study[];
};

export type CitedRow = {
  series_id: string;
  field: string;
  date: string;
  value: string;
  unit: string;
  source: string;
  source_url: string;
  retrieved_at: string;
};

export type MetricCard = {
  id: string;
  name: string;
  formula: string;
  unit: string;
  inputs: string[];
  latest_date: string;
  latest_value: string;
  question: string;
  verdict: "held" | "failed" | "flat";
  verdict_line: string;
  constants: Record<string, number | string | null>;
  study_slug: string;
};

export type MetricFile = {
  holdout_start: string;
  generated_from: string;
  note: string;
  metrics: MetricCard[];
};

export type ChangelogEntry = {
  retrieved_at: string;
  summary: string;
  changes: { id: string; before: string; after: string }[];
};

export type BookColumn = {
  key: string;
  label: string;
  unit: string;
  derived: boolean;
  formula: string;
  source: string;
  source_url: string;
  retrieved_at: string;
  z: boolean;
};

export type BookFile = {
  id: string;
  name: string;
  columns: BookColumn[];
  rows: string[][];
  z: (string | null)[][];
};

export type ToolCall = {
  name: string;
  args: Record<string, string>;
  rows: CitedRow[];
  note: string;
};
