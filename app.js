/* =============================================================
   Tn5edma — تطبيق عروض الشغل التونسي (نسخة مجانية 100%)
   يقرأ العروض مباشرة من مدونة Blogger عبر JSONP (بدون خادم)
   بوليش 2.1: مفضلة · إخفاء المنتهية · ترتيب · حفظ اختيارات · Offline
   ============================================================= */

const BLOG_URL = "https://www.tn5edma.com/";
const FB_URL = "https://www.facebook.com/share/19FyPes5yC/";
const FEED_URL = BLOG_URL + "feeds/posts/default";

const LS_FAVS = "tn5edma_favs_v1";
const LS_PREFS = "tn5edma_prefs_v1";
const LS_CACHE = "tn5edma_jobs_cache_v1";

/* خريطة الأقسام: كل قسم يجمع مجموعة من تصنيفات (labels) المدونة */
const SECTIONS = [
  { id: "all", name: "الكل", labels: [] },
  { id: "fav", name: "⭐ المفضلة", special: "fav" },
  { id: "public", name: "الوظيفة العمومية", labels: ["الوظيفة العمومية"] },
  { id: "private", name: "عروض الشغل الخاصة", labels: ["عروض الشغل الخاصة"] },
  { id: "interior", name: "وزارة الداخلية", labels: ["وزارة الداخلية"] },
  { id: "defense", name: "وزارة الدفاع الوطني", labels: ["وزارة الدفاع الوطني"] },
  {
    id: "ministries", name: "وزارات أخرى",
    labels: ["وزارات اخرى", "وزارة الصحة", "وزارة التربية", "وزارة العدل", "وزارة المالية",
      "وزارة الفلاحة والموارد المائية والصيد البحري", "وزارة النقل", "عروض وزارة النقل",
      "وزارة املاك الدولة", "وزارة تكنولوجيات الاتصال"]
  },
  { id: "abroad", name: "العمل بالخارج", labels: ["عروض الشغل بالخارج", "العمل بالخارج", "Travail à l'étranger"] },
  { id: "results", name: "نتائج المناظرات", labels: ["نتائج المناظرات"] },
];

/* أشهر تونسية + عربية فصحى + فرنسية (كاملة ومختصرة) */
const MONTHS = {
  "جانفي": 0, "يناير": 0,
  "فيفري": 1, "فبراير": 1, "فيفرييه": 1,
  "مارس": 2,
  "أفريل": 3, "افريل": 3, "أبريل": 3, "ابريل": 3,
  "ماي": 4, "مايو": 4,
  "جوان": 5, "يونيو": 5, "يونيه": 5,
  "جويلية": 6, "يوليو": 6, "يوليه": 6,
  "أوت": 7, "اوت": 7, "أغسطس": 7, "اغسطس": 7,
  "سبتمبر": 8,
  "أكتوبر": 9, "اكتوبر": 9,
  "نوفمبر": 10,
  "ديسمبر": 11,
  "janvier": 0, "janv": 0, "jan": 0,
  "février": 1, "fevrier": 1, "févr": 1, "fevr": 1, "feb": 1, "fév": 1,
  "mars": 2, "mar": 2,
  "avril": 3, "avr": 3, "apr": 3,
  "mai": 4, "may": 4,
  "juin": 5, "jun": 5,
  "juillet": 6, "juil": 6, "jul": 6,
  "août": 7, "aout": 7, "aoû": 7, "aug": 7,
  "septembre": 8, "sept": 8, "sep": 8,
  "octobre": 9, "oct": 9,
  "novembre": 10, "nov": 10,
  "décembre": 11, "decembre": 11, "déc": 11, "dec": 11
};

const PAGE_SIZE = 15;
let allJobs = [];      // كل العروض بعد التطبيع
let filtered = [];     // بعد الفلترة حسب القسم والبحث
let shown = 0;         // عدد العناصر المعروضة حالياً
let activeSection = "all";
let hiddenExpiredCount = 0;
let usingCache = false;
let currentJob = null;
let currentShare = { title: "", link: "" };

/* ===== تخزين محلي آمن ===== */
function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch (e) {
    return fallback;
  }
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (e) {
    return false;
  }
}

/* ===== المفضلة ===== */
function loadFavs() {
  const data = readJson(LS_FAVS, {});
  return data && typeof data === "object" && !Array.isArray(data) ? data : {};
}

function saveFavs(map) {
  if (!writeJson(LS_FAVS, map)) {
    showToast("تعذّر حفظ المفضلة (مساحة التخزين ممتلئة)");
  }
}

function isFav(link) {
  if (!link) return false;
  return Boolean(loadFavs()[link]);
}

function snapshotJob(job) {
  return {
    title: job.title,
    published: job.published,
    content: job.content,
    labels: job.labels || [],
    link: job.link,
    thumb: job.thumb || ""
  };
}

function toggleFav(link) {
  if (!link) return;
  const favs = loadFavs();
  if (favs[link]) {
    delete favs[link];
    saveFavs(favs);
    showToast("أُزيل من المفضلة");
  } else {
    const job = (currentJob && currentJob.link === link)
      ? currentJob
      : allJobs.find((j) => j.link === link) || loadFavs()[link];
    if (!job) return;
    favs[link] = snapshotJob(job);
    saveFavs(favs);
    showToast("أُضيف إلى المفضلة ⭐");
  }
  syncFavButtons(link);
  renderSections();
  if (activeSection === "fav") applyFilters();
}

function syncFavButtons(link) {
  const on = isFav(link);
  document.querySelectorAll(".fav-btn[data-fav-link]").forEach((btn) => {
    if (btn.getAttribute("data-fav-link") !== link) return;
    btn.classList.toggle("on", on);
    btn.textContent = on ? "★" : "☆";
    btn.setAttribute("aria-pressed", on ? "true" : "false");
  });
}

function favJobs() {
  const favs = loadFavs();
  const links = Object.keys(favs);
  const fromFeed = allJobs.filter((j) => favs[j.link]);
  const seen = new Set(fromFeed.map((j) => j.link));
  const orphans = links
    .filter((link) => !seen.has(link) && favs[link] && favs[link].title)
    .map((link) => favs[link]);
  return fromFeed.concat(orphans);
}

/* ===== تفضيلات الواجهة ===== */
function currentPrefs() {
  const searchEl = document.getElementById("searchInput");
  const hideEl = document.getElementById("hideExpired");
  const sortEl = document.getElementById("sortSelect");
  return {
    section: activeSection,
    search: searchEl ? searchEl.value : "",
    hideExpired: !!(hideEl && hideEl.checked),
    sort: sortEl ? sortEl.value : "newest"
  };
}

function savePrefs() {
  writeJson(LS_PREFS, currentPrefs());
}

function restorePrefs() {
  const p = readJson(LS_PREFS, {});
  if (!p || typeof p !== "object") return;
  if (p.section && SECTIONS.some((s) => s.id === p.section)) {
    activeSection = p.section;
  }
  const searchEl = document.getElementById("searchInput");
  const hideEl = document.getElementById("hideExpired");
  const sortEl = document.getElementById("sortSelect");
  if (searchEl && typeof p.search === "string") searchEl.value = p.search;
  if (hideEl) hideEl.checked = !!p.hideExpired;
  if (sortEl && (p.sort === "newest" || p.sort === "deadline")) sortEl.value = p.sort;
}

/* ===== كاش العروض (Offline) ===== */
function cacheJobs(jobs) {
  writeJson(LS_CACHE, {
    savedAt: Date.now(),
    jobs: jobs.map(snapshotJob)
  });
}

function loadCachedJobs() {
  const data = readJson(LS_CACHE, null);
  if (!data || !Array.isArray(data.jobs) || data.jobs.length === 0) return null;
  return data;
}

function setOfflineBanner(on, savedAt) {
  const el = document.getElementById("offlineBanner");
  if (!el) return;
  el.hidden = !on;
  if (on && savedAt) {
    const when = new Date(savedAt).toLocaleString("ar-TN", {
      day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"
    });
    el.textContent = "📴 أنت تشاهد عروضاً محفوظة (" + when + ") — اضغط ↻ عند عودة الإنترنت";
  }
}

/* ===== تحميل البيانات عبر JSONP ===== */
function loadFeed() {
  const cbName = "__tn5cb_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => { cleanup(); reject(new Error("انتهت مهلة الاتصال")); }, 15000);
    function cleanup() {
      clearTimeout(timeout);
      delete window[cbName];
      const s = document.getElementById("jsonpScript");
      if (s) s.remove();
    }
    window[cbName] = (data) => { cleanup(); resolve(data); };
    const s = document.createElement("script");
    s.id = "jsonpScript";
    s.src = `${FEED_URL}?alt=json-in-script&max-results=150&callback=${cbName}`;
    s.onerror = () => { cleanup(); reject(new Error("تعذّر الاتصال بالمدونة")); };
    document.body.appendChild(s);
  });
}

/* ===== تطبيع المدخلات ===== */
function normalize(entry) {
  const title = (entry.title && entry.title.$t) || "";
  const published = (entry.published && entry.published.$t) || "";
  const content = (entry.content && entry.content.$t) || (entry.summary && entry.summary.$t) || "";
  const labels = (entry.category || []).map((c) => c.term);
  const link = ((entry.link || []).find((l) => l.rel === "alternate") || {}).href || "";
  const thumb = (entry.media$thumbnail && entry.media$thumbnail.url) || firstImage(content) || "";
  const job = { title, published, content, labels, link, thumb };
  job._deadline = extractDeadline(content);
  return job;
}

function firstImage(html) {
  const m = String(html || "").match(/<img[^>]+src="([^"]+)"/i);
  return m ? m[1] : "";
}

function stripHtml(html) {
  const div = document.createElement("div");
  div.innerHTML = html || "";
  div.querySelectorAll("script, style").forEach((e) => e.remove());
  return div;
}

function excerpt(html, len = 170) {
  const text = stripHtml(html).textContent.replace(/\s+/g, " ").trim();
  return text.length > len ? text.slice(0, len) + "…" : text;
}

/* ===== استخراج آخر أجل (عربي بدون/بهمزة + فرنسي + رقمي) ===== */
const DEADLINE_LABEL =
  "(?:آخر\\s*أ?ج[لـ]|اخر\\s*اجل|آخر\\s*آجل|تاريخ\\s*غلق(?:\\s*الترشحات)?|" +
  "date\\s*limite(?:\\s*de\\s*(?:d[ée]p[ôo]t|candidature|soumission))?|" +
  "d[ée]lai(?:\\s*de\\s*(?:candidature|d[ée]p[ôo]t))?)";

const DATE_TOKEN =
  "(\\d{1,2}\\s*[A-Za-zÀ-ÿ\\u0600-\\u06FF]{3,14}\\s*\\d{2,4}|\\d{1,2}[\\/\\-.]\\d{1,2}[\\/\\-.]\\d{2,4})";

const DEADLINE_RE = new RegExp(DEADLINE_LABEL + "[^\\d\\n]{0,40}[:：]?\\s*" + DATE_TOKEN, "i");

function extractDeadline(content) {
  const plain = stripHtml(content).textContent.replace(/\s+/g, " ");
  const m = plain.match(DEADLINE_RE);
  if (!m) return null;
  const raw = m[1].trim();
  const parsed = parseFlexibleDate(raw);
  return { text: "آخر أجل: " + raw, date: parsed, raw };
}

function getDeadline(job) {
  if (!job) return null;
  if (job._deadline !== undefined) return job._deadline;
  job._deadline = extractDeadline(job.content);
  return job._deadline;
}

function lookupMonth(name) {
  if (!name) return undefined;
  const cleaned = String(name).replace(/[\u0640]/g, "").trim();
  if (Object.prototype.hasOwnProperty.call(MONTHS, cleaned)) return MONTHS[cleaned];
  const lower = cleaned.toLowerCase();
  if (Object.prototype.hasOwnProperty.call(MONTHS, lower)) return MONTHS[lower];
  return undefined;
}

function parseFlexibleDate(s) {
  if (!s) return null;
  const t = String(s).trim();

  let m = t.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})$/);
  if (m) {
    const day = parseInt(m[1], 10);
    const month = parseInt(m[2], 10) - 1;
    let year = parseInt(m[3], 10);
    if (year < 100) year += 2000;
    if (month < 0 || month > 11 || day < 1 || day > 31 || year < 2000) return null;
    return new Date(year, month, day);
  }

  m = t.match(/^(\d{1,2})\s+([^\s\/.\d]{3,14})\s+(\d{2,4})$/);
  if (m) {
    const day = parseInt(m[1], 10);
    const month = lookupMonth(m[2]);
    let year = parseInt(m[3], 10);
    if (year < 100) year += 2000;
    if (month === undefined || isNaN(day) || isNaN(year) || day < 1 || day > 31) return null;
    return new Date(year, month, day);
  }

  return null;
}

function deadlineState(date) {
  if (!date || isNaN(date.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = (date - today) / 86400000;
  if (diff < 0) return "expired";
  if (diff <= 7) return "soon";
  return "ok";
}

/* ===== انتماء العرض لقسم ===== */
function inSection(job, section) {
  if (!section || section.id === "all") return true;
  if (section.id === "fav" || section.special === "fav") return isFav(job.link);
  return (section.labels || []).some((l) => job.labels && job.labels.includes(l));
}

function jobsForSection(section) {
  if (!section) return allJobs.slice();
  if (section.id === "fav" || section.special === "fav") return favJobs();
  if (section.id === "all") return allJobs.slice();
  return allJobs.filter((j) => inSection(j, section));
}

function sectionOfJob(job) {
  for (const s of SECTIONS) {
    if (s.id === "all" || s.id === "fav") continue;
    if ((s.labels || []).some((l) => job.labels && job.labels.includes(l))) return s.name;
  }
  return "أخرى";
}

/* ===== تنسيق التاريخ ===== */
function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString("ar-TN", { year: "numeric", month: "long", day: "numeric" });
  } catch (e) {
    return String(iso).slice(0, 10);
  }
}

/* ===== العرض ===== */
function renderSections() {
  const nav = document.getElementById("sections");
  nav.innerHTML = "";
  SECTIONS.forEach((s) => {
    const count = jobsForSection(s).length;
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip" + (s.id === activeSection ? " active" : "") + (s.id === "fav" ? " fav" : "");
    chip.innerHTML = `${s.name} <span class="count">${count}</span>`;
    chip.onclick = () => {
      activeSection = s.id;
      savePrefs();
      applyFilters();
      renderSections();
    };
    nav.appendChild(chip);
  });
}

function applyFilters() {
  savePrefs();
  const q = (document.getElementById("searchInput").value || "").trim().toLowerCase();
  const hideExpired = !!(document.getElementById("hideExpired") && document.getElementById("hideExpired").checked);
  const sortMode = (document.getElementById("sortSelect") && document.getElementById("sortSelect").value) || "newest";
  const section = SECTIONS.find((s) => s.id === activeSection) || SECTIONS[0];

  hiddenExpiredCount = 0;
  let list = jobsForSection(section).filter((j) => {
    if (!q) return true;
    const hay = (j.title + " " + (j.labels || []).join(" ") + " " + stripHtml(j.content).textContent).toLowerCase();
    return hay.includes(q);
  });

  if (hideExpired) {
    list = list.filter((j) => {
      const dl = getDeadline(j);
      if (dl && deadlineState(dl.date) === "expired") {
        hiddenExpiredCount += 1;
        return false;
      }
      return true;
    });
  }

  if (sortMode === "deadline") {
    list.sort((a, b) => {
      const da = getDeadline(a) && getDeadline(a).date;
      const db = getDeadline(b) && getDeadline(b).date;
      const ta = da && !isNaN(da.getTime()) ? da.getTime() : null;
      const tb = db && !isNaN(db.getTime()) ? db.getTime() : null;
      if (ta === null && tb === null) return new Date(b.published) - new Date(a.published);
      if (ta === null) return 1;
      if (tb === null) return -1;
      return ta - tb;
    });
  } else {
    list.sort((a, b) => new Date(b.published) - new Date(a.published));
  }

  filtered = list;
  shown = 0;
  renderJobs(true);
  updateStatus();
}

function renderJobs(reset) {
  const list = document.getElementById("jobsList");
  if (reset) list.innerHTML = "";

  const slice = filtered.slice(shown, shown + PAGE_SIZE);
  shown += slice.length;

  if (filtered.length === 0) {
    const isFavSec = activeSection === "fav";
    const msg = isFavSec
      ? "لم تحفظ أي عرض بعد — اضغط ☆ على أي بطاقة"
      : "لا توجد عروض مطابقة";
    const emoji = isFavSec ? "⭐" : "🔎";
    list.innerHTML = `<div class="empty-state"><span class="emoji">${emoji}</span>${msg}</div>`;
    document.getElementById("loadMoreBtn").hidden = true;
    return;
  }

  slice.forEach((j) => list.appendChild(buildCard(j)));

  const moreBtn = document.getElementById("loadMoreBtn");
  moreBtn.hidden = shown >= filtered.length;
}

function buildCard(j) {
  const card = document.createElement("article");
  card.className = "job-card";
  card.onclick = () => openDetail(j);

  const thumb = j.thumb
    ? `<img class="job-thumb" loading="lazy" src="${escapeAttr(j.thumb)}" alt="" onerror="this.outerHTML='<div class=&quot;job-thumb placeholder&quot;>💼</div>'" />`
    : `<div class="job-thumb placeholder">💼</div>`;

  let deadlineBadge = "";
  const dl = getDeadline(j);
  if (dl) {
    const st = deadlineState(dl.date);
    const cls = st === "expired" ? "deadline expired" : st === "soon" ? "deadline" : "deadline ok";
    const icon = st === "expired" ? "⚠️ انتهى" : st === "soon" ? "⏰" : "✅";
    deadlineBadge = `<span class="badge ${cls}">${icon} ${escapeHtml(dl.text)}</span>`;
  }

  const favOn = isFav(j.link);

  card.innerHTML = `
    ${thumb}
    <div class="job-body">
      <div class="job-title-row">
        <h2 class="job-title">${escapeHtml(j.title)}</h2>
        <button type="button" class="fav-btn${favOn ? " on" : ""}" data-fav-link="${escapeAttr(j.link)}" aria-label="المفضلة" aria-pressed="${favOn}">${favOn ? "★" : "☆"}</button>
      </div>
      <div class="job-meta">
        <span class="badge section">${escapeHtml(sectionOfJob(j))}</span>
        <span class="badge date">🗓 ${formatDate(j.published)}</span>
        ${deadlineBadge}
      </div>
      <p class="job-excerpt">${escapeHtml(excerpt(j.content))}</p>
      <div class="job-actions">
        <a href="${escapeAttr(j.link)}" target="_blank" rel="noopener" class="btn-primary" onclick="event.stopPropagation()">اقرأ التفاصيل</a>
        <a href="${FB_URL}" target="_blank" rel="noopener" class="btn-ghost" onclick="event.stopPropagation()">تابعنا فيسبوك</a>
      </div>
    </div>`;

  const favBtn = card.querySelector(".fav-btn");
  if (favBtn) {
    favBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFav(j.link);
    });
  }
  return card;
}

function openDetail(j) {
  currentJob = j;
  currentShare = { title: j.title || "عرض شغل", link: j.link || BLOG_URL };

  const body = document.getElementById("detailBody");
  const dl = getDeadline(j);
  body.innerHTML = `
    <h2>${escapeHtml(j.title)}</h2>
    <div class="job-meta">
      <span class="badge section">${escapeHtml(sectionOfJob(j))}</span>
      <span class="badge date">🗓 ${formatDate(j.published)}</span>
      ${dl ? `<span class="badge deadline">⏰ ${escapeHtml(dl.text)}</span>` : ""}
    </div>
    ${stripHtml(j.content).innerHTML}
    <div class="detail-actions">
      <a href="${escapeAttr(j.link)}" target="_blank" rel="noopener" class="btn-primary">المصدر الأصلي ↗</a>
      <a href="${FB_URL}" target="_blank" rel="noopener" class="btn-ghost">صفحة الفايسبوك</a>
    </div>`;

  const favBtn = document.getElementById("detailFav");
  if (favBtn) {
    favBtn.setAttribute("data-fav-link", j.link || "");
    syncFavButtons(j.link);
  }

  document.getElementById("detailOverlay").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeDetail() {
  document.getElementById("detailOverlay").hidden = true;
  document.body.style.overflow = "";
}

function updateStatus() {
  const el = document.getElementById("statusText");
  let text = `${filtered.length} عرض شغل متاح الآن`;
  if (hiddenExpiredCount > 0) {
    text += ` · تم إخفاء ${hiddenExpiredCount} منتهية`;
  }
  if (usingCache) {
    text += " · 📴 بدون إنترنت";
  }
  el.textContent = text;
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(showToast._tid);
  showToast._tid = setTimeout(() => { t.hidden = true; }, 2500);
}

/* ===== أدوات التهريب ===== */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

/* ===== التهيئة ===== */
async function init() {
  restorePrefs();

  document.getElementById("refreshBtn").onclick = refresh;
  document.getElementById("loadMoreBtn").onclick = () => renderJobs(false);
  document.getElementById("detailClose").onclick = closeDetail;
  document.getElementById("detailOverlay").onclick = (e) => { if (e.target.id === "detailOverlay") closeDetail(); };
  document.getElementById("detailShare").onclick = shareCurrent;
  document.getElementById("searchInput").oninput = () => applyFilters();

  const hideEl = document.getElementById("hideExpired");
  const sortEl = document.getElementById("sortSelect");
  if (hideEl) hideEl.onchange = () => applyFilters();
  if (sortEl) sortEl.onchange = () => applyFilters();

  const detailFav = document.getElementById("detailFav");
  if (detailFav) {
    detailFav.onclick = () => {
      if (currentJob && currentJob.link) toggleFav(currentJob.link);
    };
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDetail();
  });

  await refresh();
}

async function refresh() {
  const btn = document.getElementById("refreshBtn");
  btn.classList.add("spin");
  document.getElementById("statusText").textContent = "جارِ تحميل العروض…";
  try {
    const data = await loadFeed();
    const entries = (data.feed && data.feed.entry) || [];
    allJobs = entries.map(normalize);
    allJobs.sort((a, b) => new Date(b.published) - new Date(a.published));
    cacheJobs(allJobs);
    usingCache = false;
    setOfflineBanner(false);
    renderSections();
    applyFilters();
  } catch (err) {
    const cached = loadCachedJobs();
    if (cached) {
      allJobs = cached.jobs.map((j) => {
        const job = Object.assign({}, j);
        job._deadline = extractDeadline(job.content);
        return job;
      });
      usingCache = true;
      setOfflineBanner(true, cached.savedAt);
      renderSections();
      applyFilters();
      showToast("📴 عروض محفوظة — لا يوجد اتصال");
    } else {
      document.getElementById("jobsList").innerHTML =
        `<div class="empty-state"><span class="emoji">📡</span>تعذّر تحميل العروض.<br>${escapeHtml(err.message)}</div>`;
      document.getElementById("statusText").textContent = "فشل الاتصال — اضغط ↻ للمحاولة";
    }
  } finally {
    btn.classList.remove("spin");
  }
}

/* ===== المشاركة (Web Share + نسخ الرابط) ===== */
function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise((resolve, reject) => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy") ? resolve() : reject(new Error("copy failed"));
    } catch (e) {
      reject(e);
    } finally {
      ta.remove();
    }
  });
}

function shareCurrent() {
  const title = currentShare.title || "عرض شغل";
  const url = currentShare.link || BLOG_URL;
  if (navigator.share) {
    navigator.share({ title, text: title + " — Tn5edma", url }).catch((err) => {
      if (err && err.name === "AbortError") return;
      copyText(url).then(() => showToast("تم نسخ الرابط")).catch(() => showToast("انسخ الرابط من المصدر الأصلي"));
    });
  } else {
    copyText(url).then(() => showToast("تم نسخ الرابط")).catch(() => showToast("انسخ الرابط من المصدر الأصلي"));
  }
}

/* ===== PWA ===== */
let deferredPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  document.getElementById("installBtn").hidden = false;
});
document.getElementById("installBtn").onclick = async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  document.getElementById("installBtn").hidden = true;
};

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}

init();
