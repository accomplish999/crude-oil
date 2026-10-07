"use client";

import { DitherChart } from "@/components/DitherChart";
import type { StudyChart as ChartSpec } from "@/lib/types";

export function StudyChart({ chart }: { chart: ChartSpec }) {
  return (
    <DitherChart
      stat={chart.stat}
      statLabel={chart.stat_label}
      bars={{ categories: chart.categories, series: chart.series }}
    />
  );
}
