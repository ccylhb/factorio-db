// Copies the generated leaf sitemap to a stable name (sitemap.xml) so Google
// treats it as a fresh submission and fetches it.
//
// Also injects <lastmod> from src/data/.lastmod.json — an honest ledger of when
// each URL's *content* really changed (maintained by Codex/scripts/lastmod_ledger.py).
// If the ledger is missing we simply leave the sitemap untouched: a missing
// lastmod is harmless, a wrong one teaches Google to ignore the signal.
import { copyFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const src = join(process.cwd(), "dist", "sitemap-0.xml");
const dst = join(process.cwd(), "dist", "sitemap.xml");

if (!existsSync(src)) {
  console.warn("sitemap-0.xml not found, skipping copy");
  process.exit(0);
}

let xml = readFileSync(src, "utf-8");

// ---- lastmod ---------------------------------------------------------------
const decodeEntities = (s) =>
  String(s)
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");

const norm = (p) => {
  let s = decodeEntities(p).trim();
  try {
    s = decodeURIComponent(s);
  } catch {
    /* leave as-is */
  }
  if (!s.startsWith("/")) s = "/" + s;
  if (!s.endsWith("/")) s += "/";
  return s;
};

let ledger = {};
try {
  ledger = JSON.parse(readFileSync(join(process.cwd(), "src", "data", ".lastmod.json"), "utf-8"));
} catch {
  ledger = {};
}

const LM = new Map(Object.entries(ledger).map(([k, v]) => [norm(k), v]));

// Exact hit first; otherwise fall back up the path (`/weapons/type/axe/` ->
// `/weapons/type/` -> `/weapons/`) so derived listing pages inherit the date of
// the dataset they are generated from.
const lookup = (pathname) => {
  let s = norm(pathname);
  for (let i = 0; i < 5; i += 1) {
    if (LM.has(s)) return LM.get(s);
    const trimmed = s.replace(/\/$/, "");
    const cut = trimmed.lastIndexOf("/");
    s = cut <= 0 ? "/" : trimmed.slice(0, cut + 1);
  }
  return LM.get("/") ?? null;
};

let injected = 0;
let missed = 0;

if (LM.size) {
  xml = xml.replace(/<url>[\s\S]*?<\/url>/g, (block) => {
    if (/<lastmod>/.test(block)) return block;
    const m = /<loc>\s*([\s\S]*?)\s*<\/loc>/.exec(block);
    if (!m) return block;
    let pathname = m[1];
    try {
      pathname = new URL(m[1]).pathname;
    } catch {
      /* keep raw */
    }
    const d = lookup(pathname);
    if (!d) {
      missed += 1;
      return block;
    }
    injected += 1;
    return block.replace("</url>", `  <lastmod>${d}</lastmod>\n  </url>`);
  });
  if (injected) writeFileSync(src, xml, "utf-8");
}

copyFileSync(src, dst);
console.log(
  `copied sitemap-0.xml -> sitemap.xml  (lastmod: ${injected} injected, ${missed} without` +
    (LM.size ? ")" : "; no ledger found)")
);
