import { fetchHtml } from "../lib/http.mjs";
import { extractListings } from "../lib/html.mjs";
import { parseDate, toISO } from "../lib/dates.mjs";

// Ministère de l'Intérieur — recrutement (sûreté / garde nationale / protection).
// Best-effort: la page d'accueil est très légère (contenu JS/SPA) — on tente
// quelques URLs plausibles, sinon [].
const PAGES = [
  "https://recrutementdaf.interieur.gov.tn/",
  "https://recrutementdaf.interieur.gov.tn/recrutement",
  "https://recrutementdaf.interieur.gov.tn/concours",
];
const HREF = /\/(offre|concours|recrutement|postule|inscription)s?\b/i;

export async function scrape(log) {
  const jobs = [];
  const seen = new Set();
  for (const url of PAGES) {
    log("interieur", "fetch", url);
    const html = await fetchHtml(url);
    if (!html) {
      log("interieur", "no html");
      continue;
    }
    const items = extractListings(html, HREF);
    log("interieur", `found ${items.length} links`);
    if (process.env.DEBUG && items[0]) log("interieur", "SAMPLE", items[0].context.slice(0, 400));
    for (const it of items) {
      if (seen.has(it.href)) continue;
      seen.add(it.href);
      const dt = parseDate(it.context) || parseDate(it.title);
      jobs.push({
        title: it.title,
        published: toISO(dt),
        content: it.context.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 400),
        labels: ["وزارة الداخلية"],
        link: it.href,
        thumb: "",
        source: "interieur",
        sourceLabel: "وزارة الداخلية",
      });
    }
  }
  log("interieur", `emitting ${jobs.length}`);
  return jobs;
}
