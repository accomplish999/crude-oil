"use client";

import { useState } from "react";
import type { ToolCall } from "@/lib/types";

const base = (process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(/\/$/, "");

const prompts = [
  "Latest RWTC and RBRTE, with the print date.",
  "What is CUSHING_COVER on the last week?",
  "Managed money net on CFTC_CL, last report.",
  "Which studies failed the holdout?",
];

type Turn = {
  role: "user" | "assistant";
  text: string;
  calls?: ToolCall[];
  unverified?: string[];
  mode?: string;
};

export function ChatPanel() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);

  async function ask(text: string) {
    const cleaned = text.trim();
    if (!cleaned || busy) return;
    setQuestion("");
    setTurns((current) => [...current, { role: "user", text: cleaned }]);
    setBusy(true);
    try {
      const response = await fetch(`${base}/api/chat/`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: cleaned }),
      });
      const body = (await response.json()) as {
        answer?: string;
        calls?: ToolCall[];
        unverified?: string[];
        mode?: string;
        error?: string;
      };
      setTurns((current) => [
        ...current,
        {
          role: "assistant",
          text: body.error || body.answer || "No answer.",
          calls: body.calls,
          unverified: body.unverified,
          mode: body.mode,
        },
      ]);
    } catch {
      setTurns((current) => [
        ...current,
        { role: "assistant", text: "The request failed before a tool ran." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="prompts">
        {prompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => ask(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
      <div className="thread" aria-live="polite">
        {turns.map((turn, index) => (
          <article key={`${turn.role}-${index}`} className={`bubble ${turn.role}`}>
            <p>{turn.text}</p>
            {turn.calls?.map((call, callIndex) => (
              <details key={`${call.name}-${callIndex}`} className="tool" open>
                <summary>
                  {call.name} {Object.values(call.args).filter(Boolean).join(" ")}
                </summary>
                <p>{call.note}</p>
                {call.rows.length ? (
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Series</th>
                          <th>Field</th>
                          <th>Date</th>
                          <th>Value</th>
                          <th>Source</th>
                          <th>Retrieved</th>
                        </tr>
                      </thead>
                      <tbody>
                        {call.rows.slice(0, 12).map((row) => (
                          <tr key={`${row.series_id}-${row.field}-${row.date}`}>
                            <td>{row.series_id}</td>
                            <td>{row.field}</td>
                            <td>{row.date}</td>
                            <td>{row.value}</td>
                            <td>{row.source}</td>
                            <td>{row.retrieved_at.slice(0, 10)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </details>
            ))}
            {turn.unverified && turn.unverified.length ? (
              <p className="warn">
                These figures in the reply were not in the tool rows: {turn.unverified.join(", ")}.
                Do not treat them as archive values.
              </p>
            ) : null}
          </article>
        ))}
      </div>
      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          void ask(question);
        }}
      >
        <label>
          <span className="kicker">Ask the archive</span>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="RWTC on the last print"
            disabled={busy}
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Working" : "Send"}
        </button>
      </form>
      <p className="meta-line">
        The route refuses questions that leave the archive, including requests to ignore these rules.
        A free Gemini key stays on the server. No key means the same tools answer locally, and the reply says so. Neither path is financial advice.
      </p>
    </div>
  );
}
