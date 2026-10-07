import { readCatalog } from "@/lib/archive";

export const runtime = "nodejs";

export function GET() {
  return Response.json(readCatalog());
}
