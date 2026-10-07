/** Contract math from published specs. Margin is an input. Holidays are not in the file. */

export const CONTRACTS = [
  {
    id: "CL",
    name: "NYMEX WTI",
    barrels: 1000,
    tick: 0.01,
    tickValue: 10,
    series: "RWTC",
    href: "https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html",
  },
  {
    id: "MCL",
    name: "Micro WTI",
    barrels: 100,
    tick: 0.01,
    tickValue: 1,
    series: "RWTC",
    href: "https://www.cmegroup.com/markets/energy/crude-oil/micro-wti-crude-oil.html",
  },
  {
    id: "BZ",
    name: "NYMEX Brent last day",
    barrels: 1000,
    tick: 0.01,
    tickValue: 10,
    series: "RBRTE",
    href: "https://www.cmegroup.com/markets/energy/crude-oil/brent-crude-oil-last-day.html",
  },
];

function iso(day) {
  return day.toISOString().slice(0, 10);
}

function businessDaysBefore(day, count) {
  const cursor = new Date(day.getTime());
  let left = count;
  while (left > 0) {
    cursor.setUTCDate(cursor.getUTCDate() - 1);
    const weekday = cursor.getUTCDay();
    if (weekday !== 0 && weekday !== 6) left -= 1;
  }
  return cursor;
}

export function clTermination(year, month) {
  let priorYear = year;
  let priorMonth = month - 1;
  if (priorMonth === 0) {
    priorMonth = 12;
    priorYear -= 1;
  }
  const twentyFifth = new Date(Date.UTC(priorYear, priorMonth - 1, 25));
  const weekend = twentyFifth.getUTCDay() === 0 || twentyFifth.getUTCDay() === 6;
  return businessDaysBefore(twentyFifth, weekend ? 4 : 3);
}

export function bzTermination(year, month) {
  let targetYear = year;
  let targetMonth = month - 2;
  while (targetMonth <= 0) {
    targetMonth += 12;
    targetYear -= 1;
  }
  const last = new Date(Date.UTC(targetYear, targetMonth, 0));
  while (last.getUTCDay() === 0 || last.getUTCDay() === 6) {
    last.setUTCDate(last.getUTCDate() - 1);
  }
  return last;
}

export function nextExpiry(contractId, asOfIso) {
  const asOf = new Date(`${asOfIso}T00:00:00Z`);
  const terminate = contractId === "BZ" ? bzTermination : clTermination;
  for (let step = 0; step < 24; step += 1) {
    const cursor = new Date(Date.UTC(asOf.getUTCFullYear(), asOf.getUTCMonth() + step, 1));
    const year = cursor.getUTCFullYear();
    const month = cursor.getUTCMonth() + 1;
    const term = terminate(year, month);
    if (term > asOf) {
      return {
        contract: `${cursor.toLocaleString("en-US", { month: "short", timeZone: "UTC" })} ${year}`,
        termination: iso(term),
        rule:
          contractId === "BZ"
            ? "Last weekday of the month two months before the contract month. Exchange holidays are not in this file."
            : "Three weekdays before the 25th of the prior month, or four when the 25th falls on a weekend. MCL follows CL. Exchange holidays are not in this file.",
      };
    }
  }
  return null;
}

export function nextWednesday(asOfIso) {
  const day = new Date(`${asOfIso}T00:00:00Z`);
  const weekday = day.getUTCDay();
  const add = (3 - weekday + 7) % 7 || 7;
  day.setUTCDate(day.getUTCDate() + add);
  return { date: iso(day), isReleaseWeekday: weekday === 3 };
}

export function positionSize(input) {
  const equity = Number(input.equity);
  const riskPct = Number(input.riskPct);
  const meanAbs = Number(input.meanAbs);
  const multiplier = Number(input.multiplier);
  const k = Number(input.k);
  if (!(equity > 0) || !(riskPct > 0) || !(meanAbs > 0) || !(multiplier > 0) || !(k > 0)) return null;
  const widen = input.opec ? Number(input.opecFactor) || 1 : 1;
  const stop = meanAbs * k * widen;
  const stopPer = stop * multiplier;
  if (!(stopPer > 0)) return null;
  const caps = {
    risk: Math.floor((equity * (riskPct / 100)) / stopPer),
    daily: null,
    drawdown: null,
  };
  let size = caps.risk;
  const maxDailyLoss = Number(input.maxDailyLoss);
  const p99 = Number(input.p99);
  if (maxDailyLoss > 0 && p99 > 0) {
    caps.daily = Math.floor(maxDailyLoss / (p99 * multiplier));
    size = Math.min(size, caps.daily);
  }
  const maxDd = Number(input.maxDd);
  const currentDd = Number(input.currentDd);
  if (maxDd > 0 && currentDd >= 0 && maxDd > currentDd) {
    caps.drawdown = Math.floor((equity * ((maxDd - currentDd) / 100)) / stopPer);
    size = Math.min(size, caps.drawdown);
  }
  return { size: Math.max(0, size), stop, stopPer, caps };
}

export function nearestRank(values, p) {
  const ordered = [...values].sort((a, b) => a - b);
  if (!ordered.length) return null;
  const rank = Math.ceil(p * ordered.length) - 1;
  return ordered[Math.min(ordered.length - 1, Math.max(0, rank))];
}
