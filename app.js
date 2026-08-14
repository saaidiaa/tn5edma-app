/* =============================================================
   Tn5edma — تطبيق عروض الشغل التونسي (نسخة مجانية 100%)
   يقرأ العروض مباشرة من مدونة Blogger عبر JSONP (بدون خادم)
   ============================================================= */

const BLOG_URL = "https://www.tn5edma.com/";
const FB_URL = "https://www.facebook.com/share/19FyPes5yC/";
const FEED_URL = BLOG_URL + "feeds/posts/default";

/* خريطة الأقسام: كل قسم يجمع مجموعة من تصنيفات (labels) المدونة */
const SECTIONS = [
  { id: "all", name: "الكل", labels: [] },
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

const MONTHS = {
  "جانفي": 0, "فيفري": 1, "مارس": 2, "أفريل": 3, "افريل": 3, "ماي": 4,
  "جوان": 5, "جويلية": 6, "جوان": 5, "أوت": 7, "اوت": 7, "سبتمبر": 8,
  "أكتوبر": 9, "اكتوبر": 9, "نوفمبر": 10, "ديسمبر": 11
};

const PAGE_SIZE = 15;
let allJobs = [];      // كل العروض بعد التطبيع
let filtered = [];     // بعد الفلترة حسب القسم والبحث
let shown = 0;         // عدد العناصر المعروضة حالياً
let activeSection = "all";

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
  return { title, published, content, labels, link, thumb };
}

function firstImage(html) {
  const m = html.match(/<img[^>]+src="([^"]+)"/i);
  return m ? m[1] : "";
}

function stripHtml(html) {
  const div = document.createElement("div");
  div.innerHTML = html;
  div.querySelectorAll("script, style").forEach((e) => e.remove());
  return div;
}

function excerpt(html, len = 170) {
  const text = stripHtml(html).textContent.replace(/\s+/g, " ").trim();
  return text.length > len ? text.slice(0, len) + "…" : text;
}

/* ===== استخراج آخر أجل ===== */
const DEADLINE_RE = /(?:آخر أجل|آخر آجل|تاريخ غلق الترشحات|آخر أجل للتقديم|آخر أجل للترشح|آخر أجل للترشّح)[^0-9\n]{0,20}[:：]?\s*([0-9]{1,2}\s*[^\n<،,]{2,14}\s*[0-9]{4})/i;

function extractDeadline(content) {
  const plain = stripHtml(content).textContent.replace(/\s+/g, " ");
  const m = plain.match(DEADLINE_RE);
  if (!m) return null;
  const raw = m[1].trim();
  const parsed = parseArabicDate(raw);
  return { text: "آخر أجل: " + raw, date: parsed, raw };
}

function parseArabicDate(s) {
  const m = s.match(/(\d{1,2})\s*([أ-يآ-ي]{3,10})\s*(\d{4})/);
  if (!m) return null;
  const day = parseInt(m[1], 10);
  const month = MONTHS[m[2].replace(/[\u0640]/g, "").trim()];
  const year = parseInt(m[3], 10);
  if (month === undefined || isNaN(day) || isNaN(year)) return null;
  return new Date(year, month, day);
}

function deadlineState(date) {
  if (!date) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = (date - today) / 86400000;
  if (diff < 0) return "expired";
  if (diff <= 7) return "soon";
  return "ok";
}

/* ===== انتماء العرض لقسم ===== */
function inSection(job, section) {
  if (section.id === "all") return true;
  return section.labels.some((l) => job.labels.includes(l));
}

function sectionOfJob(job) {
  for (const s of SECTIONS) {
    if (s.id === "all") continue;
    if (s.labels.some((l) => job.labels.includes(l))) return s.name;
  }
  return "أخرى";
}

/* ===== تنسيق التاريخ ===== */
function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString("ar-TN", { year: "numeric", month: "long", day: "numeric" });
  } catch (e) {
    return iso.slice(0, 10);
  }
}

/* ===== العرض ===== */
function renderSections() {
  const nav = document.getElementById("sections");
  nav.innerHTML = "";
  SECTIONS.forEach((s) => {
    const count = allJobs.filter((j) => inSection(j, s)).length;
    const chip = document.createElement("button");
    chip.className = "chip" + (s.id === activeSection ? " active" : "");
    chip.innerHTML = `${s.name} <span class="count">${count}</span>`;
    chip.onclick = () => { activeSection = s.id; applyFilters(); renderSections(); };
    nav.appendChild(chip);
  });
}

function applyFilters() {
  const q = document.getElementById("searchInput").value.trim().toLowerCase();
  const section = SECTIONS.find((s) => s.id === activeSection) || SECTIONS[0];
  filtered = allJobs.filter((j) => {
    const okSection = inSection(j, section);
    if (!okSection) return false;
    if (!q) return true;
    const hay = (j.title + " " + j.labels.join(" ") + " " + stripHtml(j.content).textContent).toLowerCase();
    return hay.includes(q);
  });
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
    list.innerHTML = `<div class="empty-state"><span class="emoji">🔎</span>لا توجد عروض مطابقة</div>`;
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
  const dl = extractDeadline(j.content);
  if (dl) {
    const st = deadlineState(dl.date);
    const cls = st === "expired" ? "deadline expired" : st === "soon" ? "deadline" : "deadline ok";
    const icon = st === "expired" ? "⚠️ انتهى" : st === "soon" ? "⏰" : "✅";
    deadlineBadge = `<span class="badge ${cls}">${icon} ${dl.text}</span>`;
  }

  card.innerHTML = `
    ${thumb}
    <div class="job-body">
      <h2 class="job-title">${escapeHtml(j.title)}</h2>
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
  return card;
}

function openDetail(j) {
  const body = document.getElementById("detailBody");
  const dl = extractDeadline(j.content);
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
  document.getElementById("detailOverlay").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeDetail() {
  document.getElementById("detailOverlay").hidden = true;
  document.body.style.overflow = "";
}

function updateStatus() {
  const el = document.getElementById("statusText");
  el.textContent = `${filtered.length} عرض شغل متاح الآن`;
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.hidden = false;
  setTimeout(() => { t.hidden = true; }, 2500);
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
  document.getElementById("refreshBtn").onclick = refresh;
  document.getElementById("loadMoreBtn").onclick = () => renderJobs(false);
  document.getElementById("detailClose").onclick = closeDetail;
  document.getElementById("detailOverlay").onclick = (e) => { if (e.target.id === "detailOverlay") closeDetail(); };
  document.getElementById("detailShare").onclick = shareCurrent;
  document.getElementById("searchInput").oninput = () => applyFilters();
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
    // ترتيب حسب تاريخ النشر (الأحدث أولاً)
    allJobs.sort((a, b) => new Date(b.published) - new Date(a.published));
    renderSections();
    applyFilters();
  } catch (err) {
    document.getElementById("jobsList").innerHTML =
      `<div class="empty-state"><span class="emoji">📡</span>تعذّر تحميل العروض.<br>${escapeHtml(err.message)}</div>`;
    document.getElementById("statusText").textContent = "فشل الاتصال — اضغط ↻ للمحاولة";
  } finally {
    btn.classList.remove("spin");
  }
}

/* ===== المشاركة ===== */
let currentShare = { title: "", link: "" };
function shareCurrent() {
  const title = (document.querySelector(".detail-body h2") || {}).textContent || "عرض شغل";
  if (navigator.share) {
    navigator.share({ title, text: title + " — Tn5edma", url: currentShare.link || BLOG_URL }).catch(() => {});
  } else {
    showToast("انسخ الرابط من زر المصدر الأصلي");
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
