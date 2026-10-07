import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const skip = new Set([
  ".git",
  "node_modules",
  ".next",
  "out",
  "public",
  ".vercel",
  ".venv",
]);

const textExt = new Set([
  ".ts",
  ".tsx",
  ".js",
  ".mjs",
  ".cjs",
  ".css",
  ".json",
  ".md",
  ".yml",
  ".yaml",
  ".html",
  ".svg",
  ".txt",
]);

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    if (skip.has(name)) continue;
    const path = join(dir, name);
    const stat = statSync(path);
    if (stat.isDirectory()) walk(path, files);
    else files.push(path);
  }
  return files;
}

const hits = [];
for (const path of walk(root)) {
  const ext = path.slice(path.lastIndexOf("."));
  if (!textExt.has(ext)) continue;
  const text = readFileSync(path, "utf8");
  const index = text.indexOf("\u2014");
  if (index !== -1) {
    const line = text.slice(0, index).split("\n").length;
    hits.push(`${path}:${line}`);
  }
}

if (hits.length) {
  console.error("Em dash (U+2014) is not allowed:");
  for (const hit of hits) console.error(hit);
  process.exit(1);
}

console.log("No em dashes.");
