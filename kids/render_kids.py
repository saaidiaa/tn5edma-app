#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_kids.py — محرّك فيديوهات تعليمية للأطفال (عمودي 1080×1920).

أنواع المشاهد المدعومة:
  intro  — ترحيب + نصّ كبير نطّاط
  count  — رقم كبير + رسوم تُعدّ وحدة وحدة (تفّاح، بالون، نجوم…)
  quiz   — سؤال، الأطفال يعدّوا، ثمّ يظهر الجواب مع نجوم
  letter — حرف عربي كبير + كلمة + رسمة
  shape  — شكل هندسي (دائرة، مربّع، مثلّث، نجمة) + اسمو
  outro  — تهنئة + كونفيتي

الاستعمال:
  python3 render_kids.py --scenes lessons/numbers_1_5.json --out out/numbers.mp4
  python3 render_kids.py --no-audio          # معاينة سريعة

المتطلبات: pip install pillow arabic-reshaper python-bidi imageio-ffmpeg
"""

import argparse
import json
import math
import os
import random
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_AR = True
except Exception:                                             # pragma: no cover
    HAS_AR = False

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- الخطوط ----
FONT_DIRS = [
    os.path.join(HERE, "assets", "fonts"),
    os.path.join(os.path.dirname(HERE), "video", "assets", "fonts"),
    "/usr/local/lib/python3.11/dist-packages/matplotlib/mpl-data/fonts/ttf",
    "/usr/share/fonts/truetype/dejavu",
]
FONT_SETS = {
    "ar":  ["Cairo.ttf", "NotoSansArabic.ttf", "DejaVuSans-Bold.ttf"],
    "num": ["Cairo.ttf", "NotoSansArabic.ttf", "DejaVuSans-Bold.ttf"],
}
_FC = {}


def _find(names):
    for n in names:
        for d in FONT_DIRS:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise RuntimeError("ما لقيتش خط: " + ", ".join(names))


def font(kind, size):
    k = (kind, size)
    if k not in _FC:
        _FC[k] = ImageFont.truetype(_find(FONT_SETS[kind]), size)
    return _FC[k]


AR_RE = re.compile(r"[\u0600-\u06FF]")
# الخطوط العربية ما فيهاش إيموجي ➜ نشيلوها باش ما تبانش مربّعات فارغة
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U0000FE0F\U0000200D]+")


def shape_txt(t):
    t = EMOJI_RE.sub("", t).strip()
    t = re.sub(r"\s{2,}", " ", t)
    if HAS_AR and AR_RE.search(t):
        return get_display(arabic_reshaper.reshape(t))
    return t


# --------------------------------------------------------------- الثيمات ---
THEMES = {
    "candy": {
        "bg1": (255, 236, 210), "bg2": (255, 205, 178),
        "accent": (255, 111, 145), "accent2": (94, 200, 229),
        "ink": (60, 42, 78), "card": (255, 255, 255),
    },
    "meadow": {
        "bg1": (222, 247, 222), "bg2": (255, 251, 214),
        "accent": (86, 186, 108), "accent2": (255, 176, 59),
        "ink": (44, 62, 48), "card": (255, 255, 255),
    },
    "ocean": {
        "bg1": (214, 240, 255), "bg2": (232, 224, 255),
        "accent": (58, 150, 221), "accent2": (255, 140, 105),
        "ink": (34, 48, 74), "card": (255, 255, 255),
    },
}
WHITE = (255, 255, 255)
SUN = (255, 199, 63)


# ------------------------------------------------------------- الحركات -----
def ease_out_back(t, s=1.9):
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * ((s + 1) * t + s) + 1.0


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def bounce(t, amp=18, freq=2.4):
    return math.sin(t * math.pi * freq) * amp


def measure(d, txt, f):
    b = d.textbbox((0, 0), txt, font=f)
    return b[2] - b[0], b[3] - b[1], b


def text_c(d, cx, cy, txt, f, fill, stroke=None, sw=0, shadow=0):
    w, h, b = measure(d, txt, f)
    x, y = cx - w / 2 - b[0], cy - h / 2 - b[1]
    if shadow:
        d.text((x + shadow, y + shadow), txt, font=f, fill=(0, 0, 0, 40))
    if stroke:
        d.text((x, y), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    else:
        d.text((x, y), txt, font=f, fill=fill)
    return w, h


# --------------------------------------------------- رسوم العدّ (vector) ---
def draw_apple(d, cx, cy, r, scale=1.0):
    r = r * scale
    d.ellipse((cx - r, cy - r * .92, cx + r, cy + r), fill=(232, 63, 71),
              outline=(120, 26, 34), width=max(2, int(r * .12)))
    d.ellipse((cx - r * .55, cy - r * .62, cx - r * .12, cy - r * .22),
              fill=(255, 160, 160))
    d.rectangle((cx - r * .09, cy - r * 1.3, cx + r * .09, cy - r * .8),
                fill=(110, 74, 40))
    d.ellipse((cx + r * .05, cy - r * 1.45, cx + r * .75, cy - r * .95),
              fill=(74, 174, 89), outline=(40, 110, 55), width=max(2, int(r * .1)))


def draw_balloon(d, cx, cy, r, scale=1.0):
    r = r * scale
    d.ellipse((cx - r * .82, cy - r * 1.05, cx + r * .82, cy + r * .85),
              fill=(94, 160, 229), outline=(38, 92, 152), width=max(2, int(r * .12)))
    d.ellipse((cx - r * .5, cy - r * .68, cx - r * .16, cy - r * .3), fill=(190, 224, 255))
    d.polygon([(cx - r * .16, cy + r * .8), (cx + r * .16, cy + r * .8),
               (cx, cy + r * 1.05)], fill=(38, 92, 152))
    d.line([(cx, cy + r * 1.05), (cx + r * .18, cy + r * 1.55),
            (cx - r * .12, cy + r * 1.95)], fill=(90, 90, 110), width=max(2, int(r * .1)))


def draw_star(d, cx, cy, r, scale=1.0):
    r = r * scale
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr = r if i % 2 == 0 else r * .45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=SUN, outline=(198, 138, 20))
    d.line(pts + [pts[0]], fill=(198, 138, 20), width=max(2, int(r * .13)), joint="curve")


def draw_heart(d, cx, cy, r, scale=1.0):
    r = r * scale
    col, edge = (240, 90, 130), (166, 40, 78)
    d.ellipse((cx - r, cy - r * .95, cx, cy + r * .05), fill=col, outline=edge,
              width=max(2, int(r * .12)))
    d.ellipse((cx, cy - r * .95, cx + r, cy + r * .05), fill=col, outline=edge,
              width=max(2, int(r * .12)))
    d.polygon([(cx - r * .96, cy - r * .18), (cx + r * .96, cy - r * .18),
               (cx, cy + r * 1.05)], fill=col)
    d.line([(cx - r * .96, cy - r * .2), (cx, cy + r * 1.05),
            (cx + r * .96, cy - r * .2)], fill=edge, width=max(2, int(r * .12)),
           joint="curve")


def draw_flower(d, cx, cy, r, scale=1.0):
    r = r * scale
    for i in range(6):
        a = math.radians(i * 60)
        px, py = cx + r * .62 * math.cos(a), cy + r * .62 * math.sin(a)
        d.ellipse((px - r * .45, py - r * .45, px + r * .45, py + r * .45),
                  fill=(214, 128, 224), outline=(140, 66, 150),
                  width=max(2, int(r * .1)))
    d.ellipse((cx - r * .38, cy - r * .38, cx + r * .38, cy + r * .38),
              fill=SUN, outline=(198, 138, 20), width=max(2, int(r * .1)))


SHAPES = {"apple": draw_apple, "balloon": draw_balloon, "star": draw_star,
          "heart": draw_heart, "flower": draw_flower}


# ------------------------------------------------------------ الخلفية ------
def make_bg(W, H, th, seed=11):
    top = Image.new("RGB", (W, H), th["bg1"])
    bot = Image.new("RGB", (W, H), th["bg2"])
    grad = Image.linear_gradient("L").resize((W, H))
    bg = Image.composite(bot, top, grad)
    d = ImageDraw.Draw(bg, "RGBA")
    rnd = random.Random(seed)
    for _ in range(22):                                    # فقاعات ناعمة
        r = rnd.randint(40, 150)
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 46))
    for _ in range(16):                                    # نجيمات باهتة
        x, y, s = rnd.randint(40, W - 40), rnd.randint(40, H - 40), rnd.randint(10, 26)
        d2 = ImageDraw.Draw(bg, "RGBA")
        pts = []
        for i in range(10):
            a = math.radians(-90 + i * 36)
            rr = s if i % 2 == 0 else s * .45
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        d2.polygon(pts, fill=(255, 255, 255, 70))
    # أرضية عشبية خفيفة
    d.rounded_rectangle((-60, H - 210, W + 60, H + 80), 120,
                        fill=(255, 255, 255, 120))
    return bg


def load_owl(name, h):
    p = os.path.join(HERE, "assets", "owl_%s.png" % name)
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if r > 240 and g > 240 and b > 240:
                px[x, y] = (r, g, b, 0)
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


def bubble(img, box, txt, f, th, tail=None):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 + 7, y0 + 9, x1 + 7, y1 + 9), 44, fill=(0, 0, 0, 55))
    d.rounded_rectangle(box, 44, fill=WHITE, outline=th["ink"], width=7)
    if tail:
        d.polygon([(tail, y1 - 4), (tail + 48, y1 - 4), (tail + 16, y1 + 44)],
                  fill=WHITE)
        d.line([(tail, y1 - 3), (tail + 16, y1 + 44), (tail + 48, y1 - 3)],
               fill=th["ink"], width=7)
    text_c(d, (x0 + x1) / 2, (y0 + y1) / 2, txt, f, th["ink"])


def confetti(d, W, H, t, seed=5):
    rnd = random.Random(seed)
    cols = [(255, 111, 145), (94, 200, 229), SUN, (128, 216, 140), (186, 148, 255)]
    for i in range(80):
        x = rnd.randint(0, W)
        sp = rnd.uniform(200, 460)
        dl = rnd.uniform(0, 1.0)
        y = -60 + (t - dl) * sp
        if y < -60 or y > H:
            continue
        s = rnd.randint(12, 26)
        k = abs(math.cos(math.radians(t * 260 + i * 41)))
        d.rectangle((x, y, x + s * (.3 + k), y + s * .6), fill=cols[i % 5])


# -------------------------------------------------------------- الإطار -----
def draw_frame(cfg, sc, t, bg, owls, idx, total):
    W, H = cfg["width"], cfg["height"]
    th = THEMES.get(cfg.get("theme", "candy"), THEMES["candy"])
    img = bg.copy().convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    kind = sc.get("type", "count")

    # ---- شريط العنوان
    f_t = font("ar", 46)
    tw, _, _ = measure(d, shape_txt(cfg["title"]), f_t)
    cw = min(W - 110, tw + 110)
    d.rounded_rectangle(((W - cw) / 2 + 7, 77, (W + cw) / 2 + 7, 187), 55,
                        fill=(0, 0, 0, 50))
    d.rounded_rectangle(((W - cw) / 2, 70, (W + cw) / 2, 180), 55,
                        fill=SUN, outline=th["ink"], width=7)
    text_c(d, W / 2, 125, shape_txt(cfg["title"]), f_t, th["ink"])

    # ---- نقاط التقدّم
    gap = 44
    for i in range(total):
        cx = W / 2 - total * gap / 2 + gap / 2 + i * gap
        col = th["accent"] if i <= idx else (255, 255, 255, 190)
        d.ellipse((cx - 12, 212 - 12, cx + 12, 212 + 12), fill=col,
                  outline=th["ink"], width=4)

    # ---- البطاقة الرئيسية
    bx0, by0, bx1, by1 = 90, 300, W - 90, 300 + 700
    pop = max(.06, ease_out_back(t / .45)) if t < .45 else 1.0
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    bw, bh = (bx1 - bx0) * pop, (by1 - by0) * pop
    card = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    d.rounded_rectangle((card[0] + 10, card[1] + 12, card[2] + 10, card[3] + 12),
                        60, fill=(0, 0, 0, 55))
    d.rounded_rectangle(card, 60, fill=th["card"], outline=th["ink"], width=9)

    if pop > .85:
        # ============ intro / outro ============
        if kind in ("intro", "outro"):
            p = ease_out((t - .5) / .5)
            if p > 0:
                sz = int(150 * (0.7 + 0.3 * p))
                f_b = font("ar", sz)
                yy = cy + bounce(t, 14)
                text_c(d, cx, yy, shape_txt(sc.get("big", "")), f_b,
                       th["accent"], stroke=th["ink"], sw=8, shadow=6)

        # ============ count ============
        elif kind == "count":
            n = int(sc.get("n", 1))
            fn = SHAPES.get(sc.get("emoji", "star"), draw_star)
            # الرقم الكبير على اليمين داخل دائرة
            pd = ease_out((t - .45) / .45)
            if pd > 0:
                rr = 150 * (0.6 + 0.4 * pd)
                dcx, dcy = bx1 - 235, by0 + 235
                d.ellipse((dcx - rr, dcy - rr, dcx + rr, dcy + rr),
                          fill=th["accent2"], outline=th["ink"], width=8)
                text_c(d, dcx, dcy, shape_txt(sc.get("digit", "")),
                       font("num", int(190 * (.7 + .3 * pd))), WHITE,
                       stroke=th["ink"], sw=7)
            # الكلمة
            pw = ease_out((t - .7) / .4)
            if pw > 0:
                text_c(d, bx0 + 265, by0 + 235, shape_txt(sc.get("word", "")),
                       font("ar", 92), th["ink"])
            # الرسوم تظهر وحدة وحدة مع صوت العدّ
            per = 0.55
            rows = math.ceil(n / 3)
            r = 92 if rows == 1 else 66
            gx = 250 if rows == 1 else 215
            gy = 178
            oy = by0 + (525 if rows == 1 else 500)
            for i in range(n):
                st = 1.0 + i * per
                pi = ease_out_back((t - st) / .45)
                if pi <= 0:
                    continue
                pi = min(pi, 1.25)
                rowi, coli = i // 3, i % 3
                incols = min(3, n - rowi * 3)
                ix = cx - (incols - 1) * gx / 2 + coli * gx
                iy = oy + rowi * gy - (rows - 1) * gy / 2 + bounce(t - st, 6, 3)
                fn(d, ix, iy, r, scale=pi)
                # رقم صغير تحت كل رسمة
                if pi > .8:
                    text_c(d, ix, iy + r + (46 if rows == 1 else 36),
                           shape_txt(str(i + 1)),
                           font("num", 46 if rows == 1 else 38), th["ink"])

        # ============ quiz ============
        elif kind == "quiz":
            n = int(sc.get("n", 3))
            fn = SHAPES.get(sc.get("emoji", "star"), draw_star)
            for i in range(n):
                pi = ease_out_back((t - (.5 + i * .25)) / .4)
                if pi <= 0:
                    continue
                ix = cx - (n - 1) * 235 / 2 + i * 235
                fn(d, ix, by0 + 275, 98, scale=min(pi, 1.2))
            # علامة استفهام نطّاطة ثم الجواب
            rv = sc.get("reveal_at", .62)
            dur = sc.get("_dur", 6.0)
            pr = (t - dur * rv) / .55
            if pr <= 0:
                q = "؟"
                text_c(d, cx, by0 + 585 + bounce(t, 16, 2.6), shape_txt(q),
                       font("ar", 190), th["accent"], stroke=th["ink"], sw=8)
            else:
                pr = min(ease_out_back(pr), 1.2)
                rr = 145 * pr
                acy = by0 + 585
                d.ellipse((cx - rr, acy - rr, cx + rr, acy + rr),
                          fill=(128, 216, 140), outline=th["ink"], width=8)
                text_c(d, cx, acy, shape_txt(sc.get("answer", "")),
                       font("num", int(175 * min(pr, 1.0))), WHITE,
                       stroke=th["ink"], sw=7)
                for i in range(6):                       # نجوم فرح
                    a = math.radians(i * 60 + t * 90)
                    sx, sy = cx + 268 * math.cos(a), acy + 128 * math.sin(a)
                    draw_star(d, sx, sy, 30 * min(1, pr))

        # ============ letter ============
        elif kind == "letter":
            pl = ease_out_back((t - .45) / .5)
            if pl > 0:
                text_c(d, cx, by0 + 280, shape_txt(sc.get("letter", "")),
                       font("ar", int(300 * min(pl, 1.05))), th["accent"],
                       stroke=th["ink"], sw=10, shadow=8)
            pw = ease_out((t - 1.1) / .45)
            if pw > 0:
                text_c(d, cx, by0 + 570, shape_txt(sc.get("word", "")),
                       font("ar", 100), th["ink"])

        # ============ shape ============
        elif kind == "shape":
            ps = ease_out_back((t - .45) / .5)
            if ps > 0:
                s = min(ps, 1.1)
                name = sc.get("shape", "circle")
                r = 195 * s
                scy = by0 + 300
                col = th["accent2"]
                if name == "circle":
                    d.ellipse((cx - r, scy - r, cx + r, scy + r), fill=col,
                              outline=th["ink"], width=9)
                elif name == "square":
                    d.rounded_rectangle((cx - r, scy - r, cx + r, scy + r), 26,
                                        fill=col, outline=th["ink"], width=9)
                elif name == "triangle":
                    d.polygon([(cx, scy - r), (cx - r, scy + r), (cx + r, scy + r)],
                              fill=col)
                    d.line([(cx, scy - r), (cx - r, scy + r), (cx + r, scy + r),
                            (cx, scy - r)], fill=th["ink"], width=9, joint="curve")
                elif name == "star":
                    draw_star(d, cx, scy, r)
            pw = ease_out((t - 1.1) / .45)
            if pw > 0:
                text_c(d, cx, by0 + 600, shape_txt(sc.get("word", "")),
                       font("ar", 100), th["ink"])

    # ---- نونو البومة
    o = owls.get(sc.get("owl", "hello"))
    if o:
        ent = ease_out_back(t / .55) if t < .55 else 1.0
        ox = W - o.width - 30
        oy = int(H - o.height - 285 + bounce(t, 13, 1.6) + (1 - ent) * 260)
        img.alpha_composite(o, (int(ox), oy))

    # ---- فقاعة الكلام
    cap = sc.get("caption", "")
    if cap:
        f_c = font("ar", 54)
        txt = shape_txt(cap)
        tw2, th2, _ = measure(d, txt, f_c)
        bw2 = min(W - 130, tw2 + 96)
        y1 = H - 235
        bubble(img, ((W - bw2) / 2, y1 - (th2 + 86), (W + bw2) / 2, y1),
               txt, f_c, th, tail=W - 320)
        d = ImageDraw.Draw(img, "RGBA")

    if sc.get("confetti"):
        confetti(d, W, H, t)

    text_c(d, W / 2, H - 82, shape_txt(cfg.get("brand", "")),
           font("ar", 38), th["ink"])
    return img.convert("RGB")


# ------------------------------------------------------------- الصوت -------
def adur(p):
    e = subprocess.run([FFMPEG, "-i", p], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e)
    if not m:
        return 4.0
    h, mm, s = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=os.path.join(HERE, "lessons", "numbers_1_5.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "lesson.mp4"))
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--tail", type=float, default=0.7)
    a = ap.parse_args()

    cfg = json.load(open(a.scenes, encoding="utf-8"))
    W, H, FPS = cfg["width"], cfg["height"], cfg["fps"]
    scenes = cfg["scenes"]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)

    durs, auds = [], []
    for sc in scenes:
        p = os.path.join(HERE, sc["audio"]) if sc.get("audio") else None
        if p and os.path.exists(p) and not a.no_audio:
            durs.append(adur(p) + a.tail)
            auds.append(p)
        else:
            durs.append(sc.get("duration", 5.0))
            auds.append(None)
        sc["_dur"] = durs[-1]

    th = THEMES.get(cfg.get("theme", "candy"), THEMES["candy"])
    bg = make_bg(W, H, th)
    owls = {n: load_owl(n, 560) for n in ("hello", "happy", "ask")}

    silent = os.path.join(HERE, "out", "_silent.mp4")
    pr = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    tot = sum(int(x * FPS) for x in durs)
    done = 0
    for i, (sc, dur) in enumerate(zip(scenes, durs)):
        for f in range(int(dur * FPS)):
            pr.stdin.write(draw_frame(cfg, sc, f / FPS, bg, owls, i,
                                      len(scenes)).tobytes())
            done += 1
            if done % 30 == 0:
                sys.stdout.write("\r  🎨 %d/%d (%d%%)" % (done, tot, 100 * done // tot))
                sys.stdout.flush()
    pr.stdin.close()
    pr.wait()
    print("\r  ✅ الصورة جاهزة" + " " * 24)

    if a.no_audio or not any(auds):
        os.replace(silent, a.out)
        print("📼", a.out)
        return

    ins, fls, lbs = [], [], []
    off, k, T = 0.0, 0, sum(durs)
    for au, dur in zip(auds, durs):
        if au:
            ins += ["-i", au]
            k += 1
            fls.append("[%d:a]adelay=%d:all=1,apad=whole_dur=%f[a%d]"
                       % (k, int(off * 1000), T, k))
            lbs.append("[a%d]" % k)
        off += dur
    mix = "".join(lbs) + "amix=inputs=%d:normalize=0[aout]" % len(lbs)
    subprocess.run([FFMPEG, "-y", "-i", silent] + ins +
                   ["-filter_complex", ";".join(fls) + ";" + mix,
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", a.out],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    os.remove(silent)
    print("📼 جاهز:", a.out, "| %.1f ثانية" % T)


if __name__ == "__main__":
    main()
