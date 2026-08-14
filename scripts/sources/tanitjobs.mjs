import { fetchHtml } from "../lib/http.mjs";
import { extractListings } from "../lib/html.mjs";
import { parseDate, toISO } from "../lib/dates.mjs";

const PAGES = ["https://www.tanitjobs.com/"];
const HREF = /\/job\/\d+\//i;

export async function scrape(log) {
  const jobs = [];
  const seen = new Set();
  for (const url of PAGES) {
    log("tanitjobs", "fetch", url);
    const html = await fetchHtml(url);
    if (!html) {
      log("tanitjobs", "no html");
      continue;
    }
    const items = extractListings(html, HREF);
    log("tanitjobs", `found ${items.length} links`);
    if (process.env.DEBUG && items[0]) log("tanitjobs", "SAMPLE", items[0].context.slice(0, 400));
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
        source: "tanitjobs",
        sourceLabel: "Tanitjobs",
      });
    }
  }
  log("tanitjobs", `emitting ${jobs.length}`);
  return jobs;
}
