// Politeness-first HTTP fetcher for the Tn5edma aggregator.
// - Identifies itself with a real UA + contact link.
// - Honors robots.txt (per-domain, cached for the run). If robots can't be
//   fetched we proceed but log a warning (we never block on it).
// - Respects Crawl-delay; adds small delays; retries on transient failures.

const UA =
  "Tn5edmaAggregator/1.0 (+https://saaidiaa.github.io/tn5edma-app/; source: github.com/saaidiaa/tn5edma-app)";

const robotsCache = new Map();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function parseRobots(text) {
  const res = { disallow: [], delay: null };
  let inBlock = false;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.split("#")[0].trim();
    if (!line) continue;
    const m = line.match(/^([A-Za-z-]+)\s*:\s*(.*)$/);
    if (!m) continue;
    const field = m[1].toLowerCase();
    const val = m[2].trim();
    if (field === "user-agent") {
      inBlock = val === "*" || /tn5edma/i.test(val);
      continue;
    }
    if (!inBlock) continue;
    if (field === "disallow") {
      if (val) res.disallow.push(val);
    } else if (field === "crawl-delay") {
      const n = parseInt(val, 10);
      if (!isNaN(n)) res.delay = n;
    }
  }
  return res;
}

async function getRobots(domain) {
  if (robotsCache.has(domain)) return robotsCache.get(domain);
  let rules = { disallow: [], delay: null };
  try {
    const r = await fetch(`https://${domain}/robots.txt`, {
      headers: { "User-Agent": UA },
      signal: AbortSignal.timeout(8000),
    });
    if (r.ok) rules = parseRobots(await r.text());
  } catch (e) {
    console.warn(`[robots] ${domain}: could not fetch robots.txt (${e.message}) — proceeding politely`);
  }
  robotsCache.set(domain, rules);
  return rules;
}

function pathAllowed(rules, pathname) {
  for (const d of rules.disallow) {
    if (d === "/") return false;
    if (d && pathname.startsWith(d)) return false;
  }
  return true;
}

export async function fetchHtml(url, { retries = 3, timeout = 20000 } = {}) {
  let u;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  const rules = await getRobots(u.hostname);
  if (!pathAllowed(rules, u.pathname)) {
    console.warn(`[robots] disallowed ${url} — skipping`);
    return null;
  }
  const delay = (rules.delay || 1) * 1000;
  if (delay > 0) await sleep(delay);

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const r = await fetch(url, {
        headers: {
          "User-Agent": UA,
          Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "fr-FR,fr;q=0.9,ar;q=0.8,en;q=0.7",
        },
        redirect: "follow",
        signal: AbortSignal.timeout(timeout),
      });
      if (r.status === 429) {
        await sleep(5000 * attempt);
        continue;
      }
      if (!r.ok) throw new Error("HTTP " + r.status);
      return await r.text();
    } catch (e) {
      if (attempt === retries) {
        console.warn(`[fetch] failed ${url}: ${e.message}`);
        return null;
      }
      await sleep(1500 * attempt);
    }
  }
  return null;
}

export { UA };
