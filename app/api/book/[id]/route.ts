import { readFileSync } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";

const books = new Set(["prices", "weekly", "positions"]);

export function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  return context.params.then((params) => {
    if (!books.has(params.id)) {
      return Response.json({ error: "Unknown book." }, { status: 404 });
    }
    const file = path.join(process.cwd(), "data", "books", `${params.id}.json`);
    const body = readFileSync(file, "utf8");
    return new Response(body, {
      headers: {
        "content-type": "application/json",
        "cache-control": "public, max-age=300",
      },
    });
  });
}
