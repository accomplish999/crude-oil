"use client";

import { useEffect, useRef } from "react";

const BAYER = [
  [0, 8, 2, 10],
  [12, 4, 14, 6],
  [3, 11, 1, 9],
  [15, 7, 13, 5],
];

type Line = { name: string; values: { x: number; y: number }[] };
type Bars = { categories: string[]; series: { name: string; values: number[] }[] };

export function DitherChart({
  stat,
  statLabel,
  lines,
  bars,
}: {
  stat: string;
  statLabel: string;
  lines?: Line[];
  bars?: Bars;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const width = canvas.clientWidth || 640;
    const height = 280;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#000";
    ctx.fillStyle = "#000";
    ctx.lineWidth = 1.25;
    ctx.font = "11px ui-monospace, monospace";

    const pad = { l: 52, r: 14, t: 16, b: 28 };
    const plotW = width - pad.l - pad.r;
    const plotH = height - pad.t - pad.b;

    if (bars) {
      const values = bars.series.flatMap((series) => series.values);
      const min = Math.min(0, ...values);
      const max = Math.max(0, ...values);
      const span = max - min || 1;
      const yOf = (value: number) => pad.t + ((max - value) / span) * plotH;
      const zero = yOf(0);
      ctx.beginPath();
      ctx.moveTo(pad.l, zero);
      ctx.lineTo(width - pad.r, zero);
      ctx.stroke();
      const group = plotW / bars.categories.length;
      const inner = bars.series.length;
      bars.categories.forEach((category, index) => {
        bars.series.forEach((series, seriesIndex) => {
          const value = series.values[index] ?? 0;
          const barW = Math.max(4, (group - 10) / inner);
          const x = pad.l + index * group + 6 + seriesIndex * barW;
          const y = yOf(value);
          const top = Math.min(y, zero);
          const h = Math.max(1, Math.abs(zero - y));
          if (seriesIndex === 0) {
            ctx.fillStyle = "#000";
            ctx.fillRect(x, top, barW - 2, h);
          } else {
            ctx.fillStyle = ditherPattern(ctx);
            ctx.fillRect(x, top, barW - 2, h);
          }
        });
        ctx.fillStyle = "#000";
        ctx.fillText(category, pad.l + index * group + 4, height - 10);
      });
      ctx.fillText(formatTick(max), 4, pad.t + 8);
      ctx.fillText(formatTick(min), 4, pad.t + plotH);
      return;
    }

    const all = (lines ?? []).flatMap((line) => line.values);
    if (!all.length) return;
    const minX = Math.min(...all.map((point) => point.x));
    const maxX = Math.max(...all.map((point) => point.x));
    const minY = Math.min(...all.map((point) => point.y));
    const maxY = Math.max(...all.map((point) => point.y));
    const spanY = maxY - minY || 1;
    const spanX = maxX - minX || 1;
    const xOf = (value: number) => pad.l + ((value - minX) / spanX) * plotW;
    const yOf = (value: number) => pad.t + ((maxY - value) / spanY) * plotH;

    (lines ?? []).forEach((line, seriesIndex) => {
      if (line.values.length < 2) return;
      ctx.beginPath();
      line.values.forEach((point, index) => {
        const x = xOf(point.x);
        const y = yOf(point.y);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      if (seriesIndex === 0) {
        const path = new Path2D();
        line.values.forEach((point, index) => {
          const x = xOf(point.x);
          const y = yOf(point.y);
          if (index === 0) path.moveTo(x, y);
          else path.lineTo(x, y);
        });
        path.lineTo(xOf(line.values[line.values.length - 1].x), yOf(minY));
        path.lineTo(xOf(line.values[0].x), yOf(minY));
        path.closePath();
        ctx.save();
        ctx.clip(path);
        ctx.fillStyle = ditherPattern(ctx);
        ctx.fillRect(pad.l, pad.t, plotW, plotH);
        ctx.restore();
        ctx.strokeStyle = "#000";
        ctx.beginPath();
        line.values.forEach((point, index) => {
          const x = xOf(point.x);
          const y = yOf(point.y);
          if (index === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        });
        ctx.stroke();
      }
    });
    ctx.fillStyle = "#000";
    ctx.fillText(formatTick(maxY), 4, pad.t + 8);
    ctx.fillText(formatTick(minY), 4, pad.t + plotH);
  }, [lines, bars]);

  const legend = bars?.series ?? lines ?? [];

  return (
    <figure className="chart-card">
      <p className="hero-num">{stat}</p>
      <p className="stat-label">{statLabel}</p>
      <div className="chart-frame">
        <canvas ref={ref} aria-label={statLabel} style={{ width: "100%", height: 280 }} />
      </div>
      <div className="chart-legend">
        {legend.map((series, index) => (
          <span key={series.name}>
            <i className={index === 0 ? "swatch solid" : "swatch dither"} />
            {series.name}
          </span>
        ))}
      </div>
    </figure>
  );
}

function ditherPattern(ctx: CanvasRenderingContext2D): CanvasPattern {
  const tile = document.createElement("canvas");
  tile.width = 4;
  tile.height = 4;
  const pen = tile.getContext("2d");
  if (!pen) throw new Error("canvas");
  pen.fillStyle = "#000";
  for (let row = 0; row < 4; row += 1) {
    for (let col = 0; col < 4; col += 1) {
      if ((BAYER[row][col] + 0.5) / 16 < 0.38) pen.fillRect(col, row, 1, 1);
    }
  }
  const pattern = ctx.createPattern(tile, "repeat");
  if (!pattern) throw new Error("pattern");
  return pattern;
}

function formatTick(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 100) return value.toFixed(0);
  if (abs >= 1) return value.toFixed(2);
  return value.toFixed(3);
}
