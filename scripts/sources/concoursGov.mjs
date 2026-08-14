import { fetchHtml } from "../lib/http.mjs";
import { extractListings } from "../lib/html.mjs";
import { parseDate, toISO } from "../lib/dates.mjs";

// Portail officiel des concours publics (Ministères, établissements & entreprises publiques)
const PAGES = [
  "https://concours.gov.tn/P1/index15.aspx?id=pub", // الجديد
  "https://concours.gov.tn/P1/index5.aspx?id=5", // المناظرات الوطنية
];
const HREF = /\/P1\/index\d+\.aspx\?id=\d+/i;

export async function scrape(log) {
  const jobs = [];
  const seen = new Set();
  for (const url of PAGES) {
    log("concours", "fetch", url);
    const html = await fetchHtml(url);
    if (!html) {
      log("concours", "no html");
      continue;
    }
    const items = extractListings(html, HREF);
    log("concours", `found ${items.length} links`);
    if (process.env.DEBUG && items[0]) log("concours", "SAMPLE", items[0].context.slice(0, 400));
    for (const it of items) {
      if (seen.has(it.href)) continue;
      seen.add(it.href);
      const dt = parseDate(it.context) || parseDate(it.title);
      jobs.push({
        title: it.title,
        published: toISO(dt),
        content: it.context.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 400),
        labels: ["الوظيفة العمومية"],
        link: it.href,
        thumb: "",
        source: "concours",
        sourceLabel: "بوابة المناظرات",
      });
    }
  }
  log("concours", `emitting ${jobs.length}`);
  return jobs;
}
