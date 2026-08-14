// Flexible date parsing for Tunisian job boards (Arabic / French / numeric).

const MONTHS = {
  janvier: 0, janv: 0, jan: 0,
  février: 1, fevrier: 1, févr: 1, fevr: 1, feb: 1, fév: 1,
  mars: 2, mar: 2,
  avril: 3, avr: 3, apr: 3,
  mai: 4, may: 4,
  juin: 5, jun: 5,
  juillet: 6, juil: 6, jul: 6,
  août: 7, aout: 7, aoû: 7, aug: 7,
  septembre: 8, sept: 8, sep: 8,
  octobre: 9, oct: 9,
  novembre: 10, nov: 10,
  décembre: 11, decembre: 11, déc: 11, dec: 11,
  جانفي: 0, يناير: 0,
  فيفري: 1, فبراير: 1, فيفرييه: 1,
  مارس: 2,
  أفريل: 3, افريل: 3, أبريل: 3, ابريل: 3,
  ماي: 4, مايو: 4,
  جوان: 5, يونيو: 5, يونيه: 5,
  جويلية: 6, يوليو: 6, يوليه: 6,
  أوت: 7, اوت: 7, أغسطس: 7, اغسطس: 7,
  سبتمبر: 8,
  أكتوبر: 9, اكتوبر: 9,
  نوفمبر: 10,
  ديسمبر: 11,
};

const REL_UNIT = {
  ثانية: 1000, دقيقة: 60000, دقائق: 60000,
  ساعة: 3600000, ساعات: 3600000,
  يوم: 86400000, أيام: 86400000,
  أسبوع: 604800000, أسابيع: 604800000,
  شهر: 2592000000, أشهر: 2592000000,
};

export function parseDate(str) {
  if (!str) return null;
  const s = String(str).trim();

  // Relative: "منذ 11 ساعة" / "منذ 5 دقيقة" / "أمس"
  if (/أمس/.test(s)) return new Date(Date.now() - 86400000);
  const rm = s.match(/منذ\s*(?:حوالي\s*)?(\d+)\s*(ثانية|دقيقة|دقائق|ساعة|ساعات|يوم|أيام|أسبوع|أسابيع|شهر|أشهر)/);
  if (rm) {
    const n = +rm[1];
    return new Date(Date.now() - n * (REL_UNIT[rm[2]] || 86400000));
  }

  // ISO
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  // DD/MM/YYYY or DD-MM-YYYY
  const m = s.match(/(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4})/);
  if (m) {
    let y = +m[3];
    if (y < 100) y += 2000;
    const d = +m[1];
    const mo = +m[2] - 1;
    if (mo >= 0 && mo < 12 && d >= 1 && d <= 31) return new Date(y, mo, d);
  }

  // DD Month YYYY (French / Arabic)
  const m2 = s.match(/(\d{1,2})\s+([A-Za-zÀ-ÿ\u0600-\u06FF]+)\s+(\d{2,4})/);
  if (m2) {
    const cleaned = m2[2].toLowerCase().replace(/[؜ـ]/g, "");
    const mo = MONTHS[cleaned];
    if (mo !== undefined) {
      let y = +m2[3];
      if (y < 100) y += 2000;
      return new Date(y, mo, +m2[1]);
    }
  }
  return null;
}

export function toISO(dt) {
  if (!dt || isNaN(dt.getTime())) return new Date().toISOString();
  return dt.toISOString();
}
