import { fetchHtml } from "../lib/http.mjs";
import { extractListings } from "../lib/html.mjs";
import { parseDate, toISO } from "../lib/dates.mjs";

// Tanqeeb (régional) — sous-domaine Tunisie => on filtre déjà sur la Tunisie.
const PAGES = [
  "https://tunisia.tanqeeb.com/ar",
  "https://tunisia.tanqeeb.com/ar/jobs-in-tunisia/all",
];
const HREF = /\/ar\/jobs(?:-in-tunisia)?\/[^\/]+\/jobs\/\d+\.html/i;
const MAX = 60;

export async function scrape(log) {
  const jobs = [];
  const seen = new Set();
  for (const url of PAGES) {
    log("tanqeeb", "fetch", url);
    const html = await fetchHtml(url);
    if (!html) {
      log("tanqeeb", "no html");
      continue;
    }
    const items = extractListings(html, HREF);
    log("tanqeeb", `found ${items.length} links`);
    if (process.env.DEBUG && items[0]) log("tanqeeb", "SAMPLE", items[0].context.slice(0, 400));
    for (const it of items) {
      if (seen.has(it.href)) continue;
      seen.add(it.href);
      const dt = parseDate(it.context) || parseDate(it.title);
      jobs.push({
        title: it.title,
        published: toISO(dt),
        content: it.context.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 400),
        labels: ["عروض الشغل الخاصة"],
        link: it.href,
        thumb: "",
        source: "tanqeeb",
        sourceLabel: "Tanqeeb",
      });
      if (jobs.length >= MAX) break;
    }
    if (jobs.length >= MAX) break;
  }
  log("tanqeeb", `emitting ${jobs.length}`);
  return jobs;
}
