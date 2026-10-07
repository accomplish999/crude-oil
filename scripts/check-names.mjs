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

function pattern(codes, flags = "") {
  return new RegExp(`\\b${String.fromCharCode(...codes)}\\b`, flags);
}

const banned = [
  pattern([65, 108, 101, 120]),
  pattern([65, 99, 99, 111, 109, 112, 108, 105, 115, 104], "i"),
  pattern(
    [77, 117, 115, 116, 97, 114, 100, 111, 108, 111, 103, 121],
    "i",
  ),
  pattern([70, 97, 106, 105, 116, 97], "i"),
  pattern([67, 105, 116, 101, 100]),
  pattern([100, 105, 116, 104, 101, 114, 117, 105], "i"),
];

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    if (skip.has(name)) continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, files);
    else files.push(path);
  }
  return files;
}

const hits = [];
for (const path of walk(root)) {
  const ext = path.slice(path.lastIndexOf("."));
  if (!textExt.has(ext)) continue;
  const lines = readFileSync(path, "utf8").split("\n");
  lines.forEach((line, index) => {
    const stripped = line.replace(/https?:\/\/\S+/g, "");
    for (const rule of banned) {
      if (rule.test(stripped)) hits.push(`${path}:${index + 1}`);
    }
  });
}

if (hits.length) {
  console.error("Banned name in copy:");
  for (const hit of hits) console.error(hit);
  process.exit(1);
}

console.log("No banned names outside URLs.");
