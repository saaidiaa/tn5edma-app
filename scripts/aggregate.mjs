// Tn5edma aggregator — orchestrator.
// Runs every source adapter in isolation (one failure never breaks the others),
// merges results, de-duplicates, and writes data/jobs.json for the app to read.

import { writeFileSync, mkdirSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";

import { scrape as tanitjobs } from "./sources/tanitjobs.mjs";
import { scrape as keejob } from "./sources/keejob.mjs";
import { scrape as concours } from "./sources/concoursGov.mjs";
import { scrape as tanqeeb } from "./sources/tanqeeb.mjs";
import { scrape as aneti } from "./sources/aneti.mjs";
import { scrape as interieur } from "./sources/interieur.mjs";
import { scrape as defense } from "./sources/defense.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..", "..");

// Excluded (blocked by Cloudflare / login walls / ToS):
//   - linkedin.com   (PerimeterX + login, anti-scraping ToS)
//   -> add later via an official API or a paid scraping service.
//   - optioncarriere.tn (Cloudflare Turnstile challenge)
const SOURCES = [
  { id: "tanitjobs", fn: tanitjobs },
  { id: "keejob", fn: keejob },
  { id: "concours", fn: concours },
  { id: "tanqeeb", fn: tanqeeb },
  { id: "aneti", fn: aneti },
  { id: "interieur", fn: interieur },
  { id: "defense", fn: defense },
];

function log(src, ...args) {
  console.log(`[${src}]`, ...args);
}

async function main() {
  const results = await Promise.allSettled(SOURCES.map((s) => s.fn(log)));
  const all = [];
  const perSource = {};

  for (let i = 0; i < SOURCES.length; i++) {
    const id = SOURCES[i].id;
    const r = results[i];
    if (r.status === "fulfilled") {
      perSource[id] = r.value.length;
      all.push(...r.value);
    } else {
      perSource[id] = `error: ${r.reason && r.reason.message ? r.reason.message : r.reason}`;
      console.error(`[${id}] FAILED`, r.reason);
    }
  }

  // Dedupe by canonical link, then by (title|source|date).
  const byLink = new Set();
  const step1 = [];
  for (const j of all) {
    const k = j.link || `${j.title}|${j.source}`;
    if (byLink.has(k)) continue;
    byLink.add(k);
    step1.push(j);
  }
  const byKey = new Set();
  const final = [];
  for (const j of step1) {
    const k = `${(j.title || "").toLowerCase()}|${j.source}|${(j.published || "").slice(0, 10)}`;
    if (byKey.has(k)) continue;
    byKey.add(k);
    final.push(j);
  }

  final.sort((a, b) => new Date(b.published) - new Date(a.published));

  const out = {
    generatedAt: new Date().toISOString(),
    sources: perSource,
    count: final.length,
    jobs: final,
  };

  const p = resolve(ROOT, "data", "jobs.json");
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(out, null, 2));
  console.log(`WROTE ${final.length} jobs to ${p}`);
  console.log("per source:", JSON.stringify(perSource));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
