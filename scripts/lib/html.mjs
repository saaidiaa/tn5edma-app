// Tiny dependency-free HTML helpers.

export function decode(s) {
  return String(s == null ? "" : s)
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n))
    .replace(/&nbsp;/g, " ");
}

export function clean(s) {
  return decode(String(s == null ? "" : s).replace(/<[^>]+>/g, ""))
    .replace(/\s+/g, " ")
    .trim();
}

// Extract anchors whose href matches `hrefRe`, returning {href, title, context}
// where context is a window of raw HTML around the anchor (useful to grab
// company / date / sector that sit next to the link).
export function extractListings(html, hrefRe) {
  const out = [];
  const re = /<a\b[^>]*\shref="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
  let m;
  while ((m = re.exec(html))) {
    const href = decode(m[1]);
    if (!hrefRe.test(href)) continue;
    const title = clean(m[2]);
    if (!title) continue;
    const idx = m.index;
    const context = html.slice(Math.max(0, idx - 400), idx + m[0].length + 600);
    out.push({ href, title, context });
  }
  return out;
}
