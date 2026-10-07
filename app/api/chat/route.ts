import { loadSeries, readMetrics, readStudies } from "@/lib/archive";
import { clientIp, guardQuestion, SYSTEM_PROMPT, takeToken } from "@/lib/guard.mjs";
import { localAnswer } from "@/lib/local-answer";
import {
  defaultField,
  largeMoves,
  latest,
  range,
  studyCall,
  unverifiedNumbers,
} from "@/lib/query";
import type { ToolCall } from "@/lib/types";

export const runtime = "nodejs";

type GeminiPart = {
  text?: string;
  functionCall?: { name: string; args?: Record<string, unknown> };
};

type GeminiResponse = {
  candidates?: { content?: { parts?: GeminiPart[] } }[];
  error?: { message?: string };
};

const declarations = [
  {
    name: "latest",
    description: "Last stored print for a series field. Use this before quoting a price, stock, or position.",
    parameters: {
      type: "OBJECT",
      properties: {
        series_id: { type: "STRING" },
        field: { type: "STRING" },
      },
      required: ["series_id"],
    },
  },
  {
    name: "range",
    description: "Observations between two dates, inclusive. At most 40 rows. Dates are YYYY-MM-DD.",
    parameters: {
      type: "OBJECT",
      properties: {
        series_id: { type: "STRING" },
        field: { type: "STRING" },
        start: { type: "STRING" },
        end: { type: "STRING" },
      },
      required: ["series_id"],
    },
  },
  {
    name: "large_moves",
    description: "Largest adjacent log changes in a single-value series. Holes longer than 5 days are ignored.",
    parameters: {
      type: "OBJECT",
      properties: {
        series_id: { type: "STRING" },
        count: { type: "NUMBER" },
      },
      required: ["series_id"],
    },
  },
  {
    name: "study",
    description: "Walk-forward result already computed in the archive. Slug is one of the study ids.",
    parameters: {
      type: "OBJECT",
      properties: { slug: { type: "STRING" } },
      required: ["slug"],
    },
  },
  {
    name: "list_series",
    description: "Ids, units, last dates, and sources in the archive.",
    parameters: { type: "OBJECT", properties: {} },
  },
  {
    name: "metric",
    description: "Derived metric: formula, last value, and the holdout verdict. Id examples: CUSHING_COVER, CURVE_Z, COT_Z, RV20, INV_SURPRISE.",
    parameters: {
      type: "OBJECT",
      properties: { id: { type: "STRING" } },
      required: ["id"],
    },
  },
];

function runTool(name: string, args: Record<string, unknown>): ToolCall {
  const series = loadSeries();
  const id = String(args.series_id ?? "");
  const file = series.get(id);
  if (name === "list_series") {
    const rows = [...series.values()].map((item) => {
      const field = defaultField(item);
      const last = [...item.observations].reverse().find((row) => row[field]);
      return {
        series_id: item.id,
        field,
        date: last?.date ?? "",
        value: last?.[field] ?? "",
        unit: item.unit,
        source: item.source,
        source_url: item.source_url,
        retrieved_at: item.retrieved_at,
      };
    });
    return {
      name,
      args: {},
      rows,
      note: `${rows.length} series.`,
    };
  }
  if (name === "study") {
    const slug = String(args.slug ?? "");
    const study = readStudies().studies.find((item) => item.slug === slug);
    if (!study) {
      return { name, args: { slug }, rows: [], note: `No study ${slug}.` };
    }
    return studyCall(study);
  }
  if (name === "metric") {
    const id = String(args.id ?? "");
    const metric = readMetrics().metrics.find(
      (item) => item.id.toLowerCase() === id.toLowerCase() || item.study_slug === id.toLowerCase(),
    );
    if (!metric) {
      return { name, args: { id }, rows: [], note: `No metric ${id}.` };
    }
    const file = series.get(metric.id);
    const row = file ? latest(file) : null;
    return {
      name,
      args: { id: metric.id },
      rows: row?.rows ?? [],
      note: `${metric.id}: ${metric.formula} Last ${metric.latest_date} ${metric.latest_value} ${metric.unit}. ${metric.verdict}. ${metric.verdict_line}`,
    };
  }
  if (!file) {
    return { name, args: { series_id: id }, rows: [], note: `No series ${id}.` };
  }
  if (name === "latest") {
    const field = args.field ? String(args.field) : defaultField(file);
    return latest(file, field);
  }
  if (name === "range") {
    const field = args.field ? String(args.field) : defaultField(file);
    return range(file, String(args.start ?? ""), String(args.end ?? ""), field, 40);
  }
  if (name === "large_moves") {
    const count = Number(args.count ?? 8);
    return largeMoves(file, Number.isFinite(count) ? count : 8);
  }
  return { name, args: {}, rows: [], note: `Unknown tool ${name}.` };
}

async function gemini(question: string): Promise<{ answer: string; calls: ToolCall[] } | null> {
  const key = process.env.GEMINI_API_KEY;
  if (!key) return null;
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";
  const catalog = [...loadSeries().values()]
    .map((item) => `${item.id} (${item.source}, ${item.frequency})`)
    .join(", ");
  const slugs = readStudies().studies.map((item) => item.slug).join(", ");
  const contents: { role: string; parts: Record<string, unknown>[] }[] = [
    { role: "user", parts: [{ text: question }] },
  ];
  const calls: ToolCall[] = [];

  for (let turn = 0; turn < 5; turn += 1) {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
      {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-goog-api-key": key,
        },
        body: JSON.stringify({
          system_instruction: {
            parts: [
              {
                text: `${SYSTEM_PROMPT} Series: ${catalog}. Study slugs: ${slugs}. Call a tool before you state a figure.`,
              },
            ],
          },
          tools: [{ function_declarations: declarations }],
          generationConfig: { maxOutputTokens: 512, temperature: 0 },
          contents,
        }),
      },
    );
    const body = (await response.json()) as GeminiResponse;
    if (!response.ok) {
      throw new Error(body.error?.message || `Gemini HTTP ${response.status}`);
    }
    const parts = body.candidates?.[0]?.content?.parts ?? [];
    const functions = parts.filter((part) => part.functionCall);
    const text = parts.map((part) => part.text ?? "").join("").trim();
    if (!functions.length) {
      return { answer: text || "The model returned no text.", calls };
    }
    contents.push({
      role: "model",
      parts: functions.map((part) => ({ functionCall: part.functionCall })),
    });
    const responses = functions.map((part) => {
      const call = part.functionCall!;
      const result = runTool(call.name, call.args ?? {});
      calls.push(result);
      return {
        functionResponse: {
          name: call.name,
          response: { note: result.note, rows: result.rows },
        },
      };
    });
    contents.push({ role: "user", parts: responses });
  }
  return {
    answer: "The model stopped after five tool rounds without a final sentence.",
    calls,
  };
}

export async function POST(request: Request) {
  if (!takeToken(clientIp(request.headers))) {
    return Response.json(
      { error: "Too many questions from this address. Wait ten minutes." },
      { status: 429 },
    );
  }
  const payload = (await request.json().catch(() => ({}))) as { question?: string };
  const gate = guardQuestion(payload.question ?? "");
  if (!gate.ok || typeof gate.question !== "string") {
    return Response.json({
      mode: "refused",
      answer: gate.answer || "Ask about a series, a metric, or a study.",
      calls: [],
      unverified: [],
    });
  }
  const question = gate.question;
  try {
    const model = await gemini(question);
    if (!model) {
      const local = localAnswer(question);
      return Response.json({ mode: "local", answer: local.answer, calls: local.calls, unverified: [] });
    }
    const evidence = JSON.stringify(model.calls);
    return Response.json({
      mode: "gemini",
      answer: model.answer,
      calls: model.calls,
      unverified: unverifiedNumbers(model.answer, evidence),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Chat failed.";
    return Response.json({ error: message }, { status: 502 });
  }
}
