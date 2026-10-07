import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const routes = new Set(["/"]);

function walk(dir, files = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".next" || name === ".venv" || name === "data") continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) walk(path, files);
    else if (/\.(tsx|ts|md|mjs)$/.test(name)) files.push(path);
  }
  return files;
}

const failures = [];
const external = new Map();

for (const file of walk(root)) {
  const text = readFileSync(file, "utf8");
  for (const match of text.matchAll(/(?:href|src)=["']([^"']+)["']/g)) {
    const ref = match[1];
    if (ref.startsWith("mailto:") || ref.startsWith("#") || ref.includes("${")) continue;
    if (ref.startsWith("http://") || ref.startsWith("https://")) {
      external.set(ref, file);
      continue;
    }
    if (ref.startsWith("/")) {
      const path = ref.split("?")[0].split("#")[0];
      if (path.startsWith("/downloads/")) {
        const local = join(root, "public", path);
        if (!existsSync(local)) failures.push(`${file}: missing download ${ref}`);
        continue;
      }
      if (path.startsWith("/notebooks/") && path.endsWith(".ipynb")) {
        const name = path.slice("/notebooks/".length);
        if (!existsSync(join(root, "notebooks", name))) failures.push(`${file}: missing notebook ${ref}`);
        continue;
      }
      const normalized = path.endsWith("/") ? path : `${path}/`;
      if (!routes.has(normalized) && !routes.has(path) && !existsSync(join(root, "public", path))) {
        failures.push(`${file}: unknown route ${ref}`);
      }
    }
  }
}

async function check(url) {
  let last = "no response";
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const response = await fetch(url, {
        redirect: "follow",
        headers: {
          "user-agent":
            "Mozilla/5.0 (compatible; crude-oil-link-check; +https://github.com/accomplish999/crude-oil)",
          accept: "text/html,application/xhtml+xml",
        },
        signal: AbortSignal.timeout(20000),
      });
      if (response.status < 400) return null;
      // CFTC serves the file to the Python ingest client and returns 403 to this runtime.
      if (response.status === 403 && new URL(url).hostname.endsWith("cftc.gov")) return null;
      last = `HTTP ${response.status}`;
      if (response.status === 403 || response.status === 429 || response.status >= 500) {
        await new Promise((resolve) => setTimeout(resolve, 600 * (attempt + 1)));
        continue;
      }
      return last;
    } catch (error) {
      last = error instanceof Error ? error.message : String(error);
      await new Promise((resolve) => setTimeout(resolve, 600 * (attempt + 1)));
    }
  }
  return last;
}

const queue = [...external.keys()];
await Promise.all(
  Array.from({ length: 4 }, async () => {
    while (queue.length) {
      const url = queue.shift();
      if (!url) return;
      const error = await check(url);
      if (error) failures.push(`${external.get(url)}: ${url} (${error})`);
    }
  }),
);

if (failures.length) {
  console.error(`Link check failed (${failures.length}):`);
  for (const failure of failures) console.error(failure);
  process.exit(1);
}

console.log(`Links ok. ${routes.size} routes, ${external.size} external URLs.`);
