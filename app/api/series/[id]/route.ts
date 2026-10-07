import { readSeries } from "@/lib/archive";

export const runtime = "nodejs";

export function GET(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  return context.params.then((params) => {
    const series = readSeries(params.id);
    if (!series) {
      return Response.json({ error: "Unknown series." }, { status: 404 });
    }
    const url = new URL(request.url);
    const start = url.searchParams.get("start") ?? "";
    const end = url.searchParams.get("end") ?? "";
    const field = url.searchParams.get("field") ?? "";
    const observations = series.observations.filter((row) => {
      if (start && row.date < start) return false;
      if (end && row.date > end) return false;
      if (field && !row[field]) return false;
      return true;
    });
    return Response.json({ ...series, observations });
  });
}
