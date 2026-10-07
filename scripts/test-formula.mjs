import assert from "node:assert/strict";
import test from "node:test";
import { evaluateFormula } from "../lib/formula.mjs";
import { clTermination, nextWednesday, positionSize } from "../lib/risk.mjs";

test("arithmetic, lag, log, and abs", () => {
  const row = { RWTC: "10", RBRTE: "4" };
  const prev = { RWTC: "8", RBRTE: "4" };
  assert.equal(evaluateFormula("RWTC-RBRTE", row, prev), "6");
  assert.equal(evaluateFormula("LAG(RWTC)", row, prev), "8");
  assert.equal(evaluateFormula("ABS(RBRTE-RWTC)", row, prev), "6");
  assert.equal(evaluateFormula("LOG(RWTC)", { RWTC: "1" }, {}), "0");
});

test("blank inputs and rejected syntax stay non-numeric", () => {
  assert.equal(evaluateFormula("RWTC-RBRTE", { RWTC: "10", RBRTE: "" }, {}), "");
  assert.throws(() => evaluateFormula("alert(1)", { RWTC: "1" }, {}));
  assert.throws(() => evaluateFormula("RWTC+", { RWTC: "1" }, {}));
});

test("July 2024 CL terminates on the weekday rule", () => {
  assert.equal(clTermination(2024, 7).toISOString().slice(0, 10), "2024-06-20");
});

test("position size is the tightest cap", () => {
  const sized = positionSize({
    equity: 100000,
    riskPct: 1,
    meanAbs: 0.5,
    multiplier: 1000,
    k: 2,
    maxDailyLoss: 1500,
    p99: 2,
    maxDd: 10,
    currentDd: 0,
    opec: false,
  });
  assert.equal(sized.caps.risk, 1);
  assert.equal(sized.caps.daily, 0);
  assert.equal(sized.size, 0);
});

test("the next Wednesday after a Tuesday is the next day", () => {
  assert.deepEqual(nextWednesday("2024-01-02"), { date: "2024-01-03", isReleaseWeekday: false });
});
