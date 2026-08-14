import { fetchHtml } from "../lib/http.mjs";
import { extractListings } from "../lib/html.mjs";
import { parseDate, toISO } from "../lib/dates.mjs";

// Ministère de la Défense Nationale — recrutement / incorporation.
// Best-effort: site WordPress, les offres sont souvent dans des sous-pages
// (direction du recrutement / formation). On tente l'accueil + quelques
// sous-pages plausibles, sinon [].
const PAGES = [
  "https://defense.tn/",
  "https://defense.tn/%D8%A7%D9%84%D8%A5%D8%AF%D8%A7%D8%B1%D8%A9-%D8%A7%D9%84%D8%B9%D8%A7%D9%85%D8%A9-%D9%84%D9%84%D8%AA%D8%AC%D9%86%D9%8A%D8%AF-%D9%88%D8%A7%D9%84%D8%AA%D8%B9%D8%A8%D8%A6%D8%A9/",
  "https://defense.tn/%D8%A7%D9%84%D8%AA%D8%AC%D9%86%D9%8A%D8%AF/",
];
const HREF = /\/(recrutement|concours|emploi|tajnid|tadjnid|%D8%AA%D8%AC%D9%86%D9%8A%D8%AF|inscription)s?\b/i;

export async function scrape(log) {
  const jobs = [];
  const seen = new Set();
  for (const url of PAGES) {
    log("defense", "fetch", url);
    const html = await fetchHtml(url);
    if (!html) {
      log("defense", "no html");
      continue;
    }
    const items = extractListings(html, HREF);
    log("defense", `found ${items.length} links`);
    if (process.env.DEBUG && items[0]) log("defense", "SAMPLE", items[0].context.slice(0, 400));
    for (const it of items) {
      if (seen.has(it.href)) continue;
      seen.add(it.href);
      const dt = parseDate(it.context) || parseDate(it.title);
      jobs.push({
        title: it.title,
        published: toISO(dt),
        content: it.context.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 400),
        labels: ["وزارة الدفاع الوطني"],
        link: it.href,
        thumb: "",
        source: "defense",
        sourceLabel: "وزارة الدفاع",
      });
    }
  }
  log("defense", `emitting ${jobs.length}`);
  return jobs;
}
