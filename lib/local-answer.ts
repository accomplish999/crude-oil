import { loadSeries, readStudies } from "@/lib/archive";
import { largeMoves, latest, range, studyCall } from "@/lib/query";
import type { ToolCall } from "@/lib/types";

function sentence(call: ToolCall): string {
  if (!call.rows.length) return call.note;
  const bits = call.rows.slice(0, 8).map((row) => {
    return `${row.series_id} ${row.field} on ${row.date} is ${row.value} (${row.unit}, ${row.source}, retrieved ${row.retrieved_at.slice(0, 10)})`;
  });
  return `${call.note} ${bits.join(". ")}.`;
}

export function localAnswer(question: string): {
  answer: string;
  calls: ToolCall[];
} {
  const text = question.toLowerCase();
  const series = loadSeries();
  const studies = readStudies().studies;
  const calls: ToolCall[] = [];

  const want = (id: string) => {
    const file = series.get(id);
    if (file) calls.push(latest(file));
  };

  if (text.includes("days of cover") || text.includes("cushing_cover")) {
    want("CUSHING_COVER");
    want("CUSHING");
    want("WCRRIUS2");
  } else if (text.includes("fail")) {
    const failed = studies.filter((study) => study.verdict === "failed");
    for (const study of failed) calls.push(studyCall(study));
  } else if (text.includes("holdout") || text.includes("stud") || text.includes("metric")) {
    for (const study of studies) calls.push(studyCall(study));
  } else if (text.includes("anomal") || text.includes("largest") || text.includes("move")) {
    const file = series.get("RWTC");
    if (file) calls.push(largeMoves(file, 6));
  } else if (text.includes("realized") || text.includes("rv20") || text.includes("volatility")) {
    want("RV20");
    want("RWTC");
  } else if (text.includes("cushing")) {
    want("CUSHING");
    want("RWTC");
  } else if (text.includes("crack")) {
    want("CRACK_321");
    want("RBOB_F1");
    want("HO_F1");
    want("RCLC1");
  } else if (
    text.includes("curve") ||
    text.includes("contango") ||
    text.includes("backward") ||
    text.includes("cl1") ||
    text.includes("term")
  ) {
    want("CL1_MINUS_CL4");
    want("RCLC1");
    want("RCLC4");
  } else if (
    text.includes("managed") ||
    text.includes("position") ||
    text.includes("cot") ||
    text.includes("cftc")
  ) {
    const file = series.get("CFTC_CL");
    if (file) {
      calls.push(latest(file, "mm_net"));
      calls.push(latest(file, "mm_net_oi"));
      calls.push(latest(file, "open_interest"));
    }
    if (text.includes("brent")) {
      const brent = series.get("CFTC_BRENT");
      if (brent) calls.push(latest(brent, "mm_net"));
    }
  } else if (text.includes("stock") || text.includes("inventory") || text.includes("spr")) {
    want("WCESTUS1");
    want("WCSSTUS1");
    want("CUSHING");
  } else if (text.includes("dollar") || text.includes("dxy") || text.includes("yield") || text.includes("rate")) {
    want("DTWEXBGS");
    want("DGS10");
    want("DGS2");
    want("DGS10_MINUS_DGS2");
  } else if (text.includes("brent") && text.includes("wti")) {
    want("RWTC");
    want("RBRTE");
  } else if (text.includes("brent")) {
    want("RBRTE");
  } else if (text.includes("wti") || text.includes("rwtc") || text.includes("crude")) {
    want("RWTC");
    want("RBRTE");
  } else if (text.includes("production") || text.includes("import") || text.includes("export") || text.includes("refin")) {
    want("WCRFPUS2");
    want("WCRRIUS2");
    want("WCRIMUS2");
    want("WCREXUS2");
    want("WPULEUS3");
  } else {
    const file = series.get("RWTC");
    if (file) calls.push(range(file, "2026-09-01", "2026-12-31", "value", 8));
  }

  const lead =
    "Local query. No model key is set, so this answer is computed from the archive. It does not use a language model.";
  const body = calls.map(sentence).join(" ");
  return { answer: `${lead} ${body}`.trim(), calls };
}
