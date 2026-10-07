"use client";

import { useMemo, useState } from "react";
import { CONTRACTS, nearestRank, nextExpiry, nextWednesday, positionSize } from "@/lib/risk.mjs";
import type { BookFile } from "@/lib/types";

export function RiskTool({
  book,
  start,
  end,
}: {
  book: BookFile | null;
  start: string;
  end: string;
}) {
  const [contractId, setContractId] = useState("MCL");
  const [equity, setEquity] = useState("250000");
  const [riskPct, setRiskPct] = useState("1");
  const [k, setK] = useState("2");
  const [margin, setMargin] = useState("");
  const [maxDailyLoss, setMaxDailyLoss] = useState("25000");
  const [maxDd, setMaxDd] = useState("10");
  const [currentDd, setCurrentDd] = useState("0");
  const [opec, setOpec] = useState(false);

  const contract = CONTRACTS.find((item) => item.id === contractId) ?? CONTRACTS[0];
  const sample = useMemo(() => buildSample(book, contract.series, start, end), [book, contract.series, start, end]);
  const sized = sample
    ? positionSize({
        equity,
        riskPct,
        meanAbs: sample.meanAbs,
        multiplier: contract.barrels,
        k,
        maxDailyLoss,
        p99: sample.p99,
        maxDd,
        currentDd,
        opec,
        opecFactor: 1.5,
      })
    : null;
  const expiry = sample ? nextExpiry(contract.id, sample.asOf) : null;
  const release = sample ? nextWednesday(sample.asOf) : null;
  const marginNum = Number(margin);
  const marginContracts =
    sized && marginNum > 0 ? Math.floor(Number(equity) / marginNum) : null;

  return (
    <section className="panel" id="risk">
      <h2>Risk worksheet</h2>
      <p className="meta-line">
        Tick value is the contract spec. Margin is whatever your clearing statement says today. This archive does not store a live margin.
        The volatility sample is the mean absolute close-to-close change over the last 14 gaps of 1 to 5 days inside the date window.
        EIA posts one price, so this is not a high-low ATR. Regime filter does not enter this sample.
      </p>
      <div className="controls risk-controls">
        <label>
          <span>Contract</span>
          <select value={contractId} onChange={(event) => setContractId(event.target.value)}>
            {CONTRACTS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Equity $</span>
          <input value={equity} onChange={(event) => setEquity(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          <span>Risk %</span>
          <input value={riskPct} onChange={(event) => setRiskPct(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          <span>Stop, k times move</span>
          <input value={k} onChange={(event) => setK(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          <span>Initial margin $</span>
          <input value={margin} onChange={(event) => setMargin(event.target.value)} inputMode="decimal" placeholder="from the clearer" />
        </label>
        <label>
          <span>Max daily loss $</span>
          <input value={maxDailyLoss} onChange={(event) => setMaxDailyLoss(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          <span>Max drawdown %</span>
          <input value={maxDd} onChange={(event) => setMaxDd(event.target.value)} inputMode="decimal" />
        </label>
        <label>
          <span>Current drawdown %</span>
          <input value={currentDd} onChange={(event) => setCurrentDd(event.target.value)} inputMode="decimal" />
        </label>
      </div>
      <label className="check">
        <input type="checkbox" checked={opec} onChange={(event) => setOpec(event.target.checked)} />
        OPEC window. Widens the stop by 1.5. This file has no OPEC calendar, so the switch is manual.
      </label>
      {sample && sized && expiry && release ? (
        <div className="stat-row risk-stats">
          <div className="stat">
            <span className="label">Contracts</span>
            <strong>{sized.size}</strong>
            <em>
              Budget {money((Number(equity) * Number(riskPct)) / 100)}
              <br />
              Stop needs {money(sized.stopPer)}
            </em>
          </div>
          <div className="stat">
            <span className="label">14-print move</span>
            <strong>{sample.meanAbs.toFixed(2)}</strong>
            <em>
              {sample.asOf}
              <br />
              p99 gap {sample.p99.toFixed(2)}
            </em>
          </div>
          <div className="stat">
            <span className="label">Caps</span>
            <strong>{sized.caps.risk}</strong>
            <em>
              Risk cap {sized.caps.risk}. Daily cap {sized.caps.daily ?? "n/a"}. Drawdown cap {sized.caps.drawdown ?? "n/a"}.
              {marginContracts != null ? ` Margin cap ${marginContracts}.` : " Margin not entered."}
            </em>
          </div>
          <div className="stat">
            <span className="label">Calendar</span>
            <strong>{expiry.termination.slice(5)}</strong>
            <em>
              {expiry.contract} rule date {expiry.termination}
              <br />
              Next Wednesday {release.date}
              {release.isReleaseWeekday ? ". The as-of print is a Wednesday." : "."}
            </em>
          </div>
        </div>
      ) : (
        <p>The date window does not have 14 usable closes for {contract.series}.</p>
      )}
      <p className="meta-line">
        {contract.id} is {contract.barrels.toLocaleString("en-US")} barrels. Tick {contract.tick} is ${contract.tickValue}. One dollar per barrel is ${contract.barrels.toLocaleString("en-US")} a contract.
        Size is the minimum of the risk cap, the daily-loss cap against the in-window 99th percentile close-to-close gap, and the unused drawdown room.
        {expiry ? ` ${expiry.rule}` : ""} Spec: <a href={contract.href}>{contract.name}</a>.
      </p>
    </section>
  );
}

function buildSample(book: BookFile | null, seriesId: string, start: string, end: string) {
  if (!book) return null;
  const index = book.columns.findIndex((column) => column.key === seriesId);
  if (index < 0) return null;
  const points = book.rows
    .map((row) => ({ date: row[0], value: row[index] }))
    .filter((point) => point.value && (!start || point.date >= start) && (!end || point.date <= end));
  const moves: number[] = [];
  for (let i = 1; i < points.length; i += 1) {
    const gap = Math.round(
      (Date.parse(`${points[i].date}T00:00:00Z`) - Date.parse(`${points[i - 1].date}T00:00:00Z`)) / 86400000,
    );
    if (gap < 1 || gap > 5) continue;
    moves.push(Math.abs(Number(points[i].value) - Number(points[i - 1].value)));
  }
  const last = moves.slice(-14);
  if (last.length < 14) return null;
  const meanAbs = last.reduce((sum, value) => sum + value, 0) / last.length;
  const p99 = nearestRank(moves, 0.99);
  if (p99 == null) return null;
  return { meanAbs, p99, asOf: points[points.length - 1].date };
}

function money(value: number) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}
