import { fetchHtml } from "../lib/http.mjs";
import { extractListings } from "../lib/html.mjs";
import { parseDate, toISO } from "../lib/dates.mjs";

// ANETI — Agence Nationale pour l'Emploi et le Travail Indépendant.
// (Secteur privé, programmes d'intégration SIVP / Karama). Best-effort: le site
// est souvent dynamique / instable (HTTP 500 observé) — on réessaie, sinon [].
const PAGES = [
  "https://emploi.nat.tn/",
  "https://emploi.nat.tn/Offres",
  "https://www.emploi.nat.tn/recherche-offres",
];
const HREF = /\/(offre|emploi|recrutement|offres|job)s?\b/i;

export async function scrape(log) {
  const jobs = [];
  const seen = new Set();
  for (const url of PAGES) {
    log("aneti", "fetch", url);
    const html = await fetchHtml(url);
    if (!html) {
      log("aneti", "no html");
      continue;
    }
    const items = extractListings(html, HREF);
    log("aneti", `found ${items.length} links`);
    if (process.env.DEBUG && items[0]) log("aneti", "SAMPLE", items[0].context.slice(0, 400));
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
        source: "aneti",
        sourceLabel: "ANETI",
      });
    }
  }
  log("aneti", `emitting ${jobs.length}`);
  return jobs;
}
