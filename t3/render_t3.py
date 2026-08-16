#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_t3.py — محرّك حلقات يوتيوب تعليمية «السنة الثالثة أساسي» (أفقي 1920×1080).

الفكرة: لوحة بيضاء على اليسار (الخطوات والأرقام اللاتينية) + صورة واقعية على
اليمين + تعليق صوتي. كل حلقة = ملف JSON واحد.

الاستعمال:
  python3 render_t3.py --scenes lessons/ep1_numbers.json --out out/ep1.mp4
  python3 render_t3.py --scenes ... --no-audio      # معاينة سريعة

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
except Exception:                                            # pragma: no cover
    HAS_AR = False

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- الخطوط ----
FONT_DIRS = [
    os.path.join(HERE, "assets", "fonts"),
    os.path.join(os.path.dirname(HERE), "video", "assets", "fonts"),
    "/usr/share/fonts/truetype/dejavu",
]
FONT_SETS = {
    "ar":   ["Cairo.ttf", "NotoSansArabic.ttf", "DejaVuSans-Bold.ttf"],
    "num":  ["DejaVuSans-Bold.ttf"],
    "reg":  ["DejaVuSans.ttf"],
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
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U0000FE0F\U0000200D]+")


def shape(txt):
    txt = EMOJI_RE.sub("", txt).strip()
    if HAS_AR and AR_RE.search(txt):
        return get_display(arabic_reshaper.reshape(txt))
    return txt


# ---------------------------------------------------------------- الألوان ---
PAPER     = (250, 247, 240)
GRID      = (233, 227, 214)
INK       = (30, 34, 44)
BLUE      = (36, 99, 235)
BLUE_DARK = (23, 65, 156)
CORAL     = (235, 87, 74)
SUN       = (255, 199, 44)
GREEN     = (34, 168, 96)
VIOLET    = (124, 92, 214)
TEAL      = (16, 138, 141)
WHITE     = (255, 255, 255)

STYLE = {
    "eq":     (INK,    96),
    "op":     (CORAL,  84),
    "ask":    (VIOLET, 88),
    "answer": (GREEN,  100),
    "label":  (TEAL,   46),
    "small":  (INK,    56),
}


# ------------------------------------------------------- أدوات الرسم -------
def ease_out_back(t, s=1.7):
    t = max(0.0, min(1.0, t))
    t -= 1.0
    return t * t * ((s + 1) * t + s) + 1.0


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def measure(draw, txt, fnt):
    b = draw.textbbox((0, 0), txt, font=fnt)
    return b[2] - b[0], b[3] - b[1], b


def text_center(draw, cx, cy, txt, fnt, fill):
    w, h, b = measure(draw, txt, fnt)
    draw.text((cx - w / 2 - b[0], cy - h / 2 - b[1]), txt, font=fnt, fill=fill)
    return w, h


def font_fit(draw, kind, size, txt, max_w):
    """يصغّر الخط تدريجياً حتى يسع النص في العرض المحدد."""
    f = font(kind, size)
    w, _, _ = measure(draw, txt, f)
    while w > max_w and size > 24:
        size = int(size * 0.93)
        f = font(kind, size)
        w, _, _ = measure(draw, txt, f)
    return f


def card(img, box, radius=42, fill=WHITE, line=INK, w=7, shadow=12):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    if shadow:
        d.rounded_rectangle((x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow),
                            radius, fill=(0, 0, 0, 60) if img.mode == "RGBA" else INK)
    d.rounded_rectangle(box, radius, fill=fill, outline=line, width=w)


def make_background(W, H, seed=11):
    bg = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(bg)
    step = 64
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=GRID, width=2)
    for y in range(0, H, step):
        d.line([(0, y), (H * 2, y)], fill=GRID, width=2)
    rnd = random.Random(seed)
    doodles = ["+", "-", "×", "÷", "=", "?", "123", "%"]
    faint = (228, 220, 203)
    for _ in range(22):
        f = font("num", rnd.randint(40, 90))
        d.text((rnd.randint(-20, W - 60), rnd.randint(-20, H - 80)),
               rnd.choice(doodles), font=f, fill=faint)
    top = Image.new("RGB", (W, H), BLUE)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-W * 0.3, -H * 0.35, W * 1.3, H * 0.16), fill=42)
    md.ellipse((-W * 0.3, H * 0.9, W * 1.3, H * 1.35), fill=34)
    bg = Image.composite(top, bg, mask.filter(ImageFilter.GaussianBlur(80)))
    return bg


_PHOTO_CACHE = {}


def load_photo(rel, box_w, box_h, radius=38):
    """صورة واقعية مقصوصة بزوايا مدوّرة تسدّ الإطار."""
    key = (rel, box_w, box_h)
    if key in _PHOTO_CACHE:
        return _PHOTO_CACHE[key]
    p = os.path.join(HERE, rel)
    im = Image.open(p).convert("RGB")
    scale = max(box_w / im.width, box_h / im.height)
    im = im.resize((int(im.width * scale) + 1, int(im.height * scale) + 1),
                   Image.LANCZOS)
    x = (im.width - box_w) // 2
    y = (im.height - box_h) // 2
    im = im.crop((x, y, x + box_w, y + box_h))
    mask = Image.new("L", (box_w, box_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, box_w - 1, box_h - 1),
                                           radius, fill=255)
    out = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    _PHOTO_CACHE[key] = out
    return out


def hand_ellipse(draw, box, color, progress, width=9, seed=3):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    rnd = random.Random(seed)
    total = 2.35 * math.pi
    n = max(2, int(120 * progress))
    pts = []
    for i in range(n):
        a = -0.5 + total * (i / 120.0)
        wob = 1 + 0.022 * math.sin(a * 3 + seed) + rnd.uniform(-0.006, 0.006)
        pts.append((cx + rx * wob * math.cos(a), cy + ry * wob * math.sin(a)))
    if len(pts) > 1:
        draw.line(pts, fill=color, width=width, joint="curve")


# ------------------------------------------------- جينيريك المقدمة ---------
_LOGO = None


def load_logo(height):
    global _LOGO
    if _LOGO is not None and _LOGO.height == height:
        return _LOGO
    p = os.path.join(HERE, "assets", "brand", "logo.png")
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    px = im.load()
    w, h = im.size
    for yy in range(h):
        for xx in range(w):
            r, g, b, a = px[xx, yy]
            if r > 244 and g > 244 and b > 244:
                px[xx, yy] = (r, g, b, 0)
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    ratio = height / im.height
    _LOGO = im.resize((max(1, int(im.width * ratio)), height), Image.LANCZOS)
    return _LOGO


def draw_intro(cfg, t, dur, bg):
    """جينيريك احترافي: اللوغو يهبط + العنوان + شارة الحلقة + نجوم."""
    W, H = cfg["width"], cfg["height"]
    frame = bg.copy().convert("RGBA")
    d = ImageDraw.Draw(frame)

    # ستارة زرقاء تفتح
    open_p = ease_out(t / 0.45)
    cw = int((W / 2) * (1 - open_p))
    if cw > 0:
        d.rectangle((0, 0, cw, H), fill=BLUE_DARK)
        d.rectangle((W - cw, 0, W, H), fill=BLUE_DARK)

    # نجوم متلألئة
    rnd = random.Random(5)
    for i in range(26):
        sx, sy = rnd.randint(40, W - 40), rnd.randint(40, H - 40)
        ph = (t * 2 + i * 0.7) % 2
        s = 6 + 5 * max(0.0, math.sin(ph * math.pi))
        col = [SUN, CORAL, TEAL][i % 3]
        d.polygon([(sx, sy - s), (sx + s * 0.35, sy - s * 0.35), (sx + s, sy),
                   (sx + s * 0.35, sy + s * 0.35), (sx, sy + s),
                   (sx - s * 0.35, sy + s * 0.35), (sx - s, sy),
                   (sx - s * 0.35, sy - s * 0.35)], fill=col)

    # اللوغو يهبط بنطة
    logo = load_logo(int(H * 0.42))
    if logo:
        entry = ease_out_back((t - 0.25) / 0.6) if t > 0.25 else 0.0
        ly = int(H * 0.10 + (1 - entry) * (-H * 0.5))
        frame.alpha_composite(logo, ((W - logo.width) // 2, ly))
        d = ImageDraw.Draw(frame)

    # العنوان
    p2 = ease_out((t - 1.0) / 0.5)
    if p2 > 0:
        f_t = font("ar", int(84 * (0.85 + 0.15 * p2)))
        txt = shape(cfg.get("title", ""))
        tw, th, _ = measure(d, txt, f_t)
        y0 = int(H * 0.60)
        pad = 40
        card(frame, (W / 2 - tw / 2 - pad, y0, W / 2 + tw / 2 + pad,
                     y0 + th + 56), radius=40, fill=SUN, w=8, shadow=12)
        d = ImageDraw.Draw(frame)
        text_center(d, W / 2, y0 + (th + 56) / 2, txt, f_t, INK)

    # شارة الحلقة
    p3 = ease_out((t - 1.5) / 0.4)
    ep = cfg.get("episode", "")
    if p3 > 0 and ep:
        f_e = font("num", 62)
        et = "EPISODE %s" % ep
        ew, eh, _ = measure(d, et, f_e)
        y1 = int(H * 0.60) + 170
        card(frame, (W / 2 - ew / 2 - 34, y1, W / 2 + ew / 2 + 34,
                     y1 + eh + 40), radius=36, fill=CORAL, w=7, shadow=10)
        d = ImageDraw.Draw(frame)
        text_center(d, W / 2, y1 + (eh + 40) / 2, et, f_e, WHITE)

    # التوقيع
    f_b = font("ar", 40)
    text_center(d, W / 2, H - 60, shape(cfg.get("brand", "")), f_b, BLUE_DARK)
    return frame.convert("RGB")


# ------------------------------------------------------------- الإطار ------
def draw_frame(cfg, scene, t, dur, bg, idx, total):
    W, H = cfg["width"], cfg["height"]
    vertical = H > W                       # 9:16 → Shorts / Reels
    frame = bg.copy().convert("RGBA")
    d = ImageDraw.Draw(frame)

    # --- الشريط العلوي: شارة الحلقة + العنوان
    f_title = font("ar", 52 if not vertical else 56)
    title = shape(cfg.get("title", ""))
    tw, th, _ = measure(d, title, f_title)
    chip_w = min(tw + 130, W - (270 if not vertical else 120))
    ty0, ty1 = (34, 128) if not vertical else (60, 170)
    card(frame, (W / 2 - chip_w / 2, ty0, W / 2 + chip_w / 2, ty1),
         radius=48, fill=SUN, w=6, shadow=8)
    d = ImageDraw.Draw(frame)
    text_center(d, W / 2, (ty0 + ty1) / 2 - 3, title, f_title, INK)

    ep = cfg.get("episode", "")
    if ep and not vertical:
        f_ep = font("num", 46)
        card(frame, (54, 34, 234, 128), radius=48, fill=CORAL, w=6, shadow=8)
        d = ImageDraw.Draw(frame)
        text_center(d, 144, 78, "EP %s" % ep, f_ep, WHITE)

    # --- نقاط التقدّم
    dot_r, gap = 11, 40
    tot_w = total * gap
    dot_y = 162 if not vertical else 214
    for i in range(total):
        cx = W / 2 - tot_w / 2 + gap / 2 + i * gap
        col = BLUE if i <= idx else (215, 208, 191)
        d.ellipse((cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r),
                  fill=col, outline=INK, width=3)

    if vertical:
        return _draw_vertical(cfg, scene, t, dur, frame, idx)

    # --- الصورة الواقعية (يمين)
    ph_w, ph_h = 700, 470
    px0, py0 = W - ph_w - 80, 220
    img_rel = scene.get("image")
    if img_rel:
        slide = ease_out(t / 0.5)
        ph = load_photo(img_rel, ph_w, ph_h)
        ox = int((1 - slide) * 260)
        card(frame, (px0 - 10, py0 - 10, px0 + ph_w + 10, py0 + ph_h + 10),
             radius=44, fill=WHITE, w=8, shadow=14)
        frame.alpha_composite(ph, (px0 + ox, py0))
        d = ImageDraw.Draw(frame)

    # --- فقاعة التعليق تحت الصورة
    cap = scene.get("caption", "")
    if cap:
        txt = shape(cap)
        f_cap = font_fit(d, "ar", 46, txt, ph_w - 30)
        cw, ch, _ = measure(d, txt, f_cap)
        bw2 = min(ph_w + 40, cw + 80)
        bx = px0 + ph_w / 2
        y0c = py0 + ph_h + 40
        card(frame, (bx - bw2 / 2, y0c, bx + bw2 / 2, y0c + ch + 56),
             radius=34, fill=WHITE, w=6, shadow=8)
        d = ImageDraw.Draw(frame)
        text_center(d, bx, y0c + (ch + 56) / 2, txt, f_cap, BLUE_DARK)

    # --- اللوحة (يسار)
    bx0, by0 = 80, 220
    bx1, by1 = W - ph_w - 190, H - 130
    pop = max(0.06, ease_out_back(t / 0.40)) if t < 0.40 else 1.0
    bw, bh = (bx1 - bx0) * pop, (by1 - by0) * pop
    ccx, ccy = (bx0 + bx1) / 2, (by0 + by1) / 2
    board = (ccx - bw / 2, ccy - bh / 2, ccx + bw / 2, ccy + bh / 2)
    card(frame, board, radius=48, fill=WHITE, w=8, shadow=14)
    d = ImageDraw.Draw(frame)

    if pop > 0.85:
        f_bt = font("ar", 44)
        bt = shape(scene.get("board_title", ""))
        if bt:
            tw2, th2, _ = measure(d, bt, f_bt)
            pad = 28
            d.rounded_rectangle((ccx - tw2 / 2 - pad, by0 + 30,
                                 ccx + tw2 / 2 + pad, by0 + 30 + th2 + 26),
                                26, fill=TEAL)
            text_center(d, ccx, by0 + 30 + (th2 + 26) / 2, bt, f_bt, WHITE)

        lines = scene.get("lines", [])
        base_y = by0 + 140
        slot = (by1 - 50 - base_y) / max(1, len(lines))
        for i, ln in enumerate(lines):
            start = 0.5 + i * 0.55
            p = ease_out((t - start) / 0.45)
            if p <= 0:
                continue
            style = ln.get("style", "eq")
            col, size = STYLE.get(style, STYLE["eq"])
            kind = "ar" if AR_RE.search(ln["text"]) else "num"
            txt = shape(ln["text"])
            f_eq = font_fit(d, kind, int(size * (0.9 + 0.1 * p)), txt,
                            (bx1 - bx0) - 110)
            y = base_y + slot * (i + 0.5) + (1 - p) * 36
            w_, h_, b_ = measure(d, txt, f_eq)
            x_ = ccx - w_ / 2 - b_[0]
            d.text((x_ + 4, y - h_ / 2 - b_[1] + 4), txt, font=f_eq,
                   fill=(0, 0, 0, int(40 * p)))
            d.text((x_, y - h_ / 2 - b_[1]), txt, font=f_eq, fill=col)
            if style == "answer":
                pr = ease_out((t - (start + 0.5)) / 0.7)
                if pr > 0:
                    hand_ellipse(d, (ccx - w_ / 2 - 55, y - h_ / 2 - 40,
                                     ccx + w_ / 2 + 55, y + h_ / 2 + 40),
                                 CORAL, pr, width=10, seed=idx + 2)

    # --- كونفيتي
    if scene.get("confetti"):
        rnd = random.Random(99)
        for i in range(80):
            sx = rnd.randint(0, W)
            sp = rnd.uniform(180, 430)
            delay = rnd.uniform(0, 0.9)
            yy = -60 + (t - delay) * sp
            if yy < -60 or yy > H:
                continue
            c = [CORAL, SUN, BLUE, GREEN, VIOLET][i % 5]
            s = rnd.randint(10, 22)
            ang = (t * 240 + i * 37) % 360
            k = abs(math.cos(math.radians(ang)))
            d.rectangle((sx, yy, sx + s * (0.3 + k), yy + s * 0.6), fill=c)

    # --- التوقيع
    f_b = font("ar", 36)
    text_center(d, W / 2, H - 52, shape(cfg.get("brand", "")), f_b, BLUE_DARK)
    return frame.convert("RGB")


# -------------------------------------------------- التخطيط العمودي 9:16 ---
def _draw_vertical(cfg, scene, t, dur, frame, idx):
    """Shorts/Reels: الصورة فوق، اللوحة تحت، الفقاعة بينهما."""
    W, H = cfg["width"], cfg["height"]
    d = ImageDraw.Draw(frame)

    # --- الصورة الواقعية (فوق)
    ph_w, ph_h = W - 140, 560
    px0, py0 = 70, 260
    img_rel = scene.get("image")
    if img_rel:
        slide = ease_out(t / 0.5)
        ph = load_photo(img_rel, ph_w, ph_h)
        oy = int((1 - slide) * -180)
        card(frame, (px0 - 10, py0 - 10, px0 + ph_w + 10, py0 + ph_h + 10),
             radius=44, fill=WHITE, w=8, shadow=14)
        frame.alpha_composite(ph, (px0, py0 + oy if py0 + oy > 180 else py0))
        d = ImageDraw.Draw(frame)

    # --- الفقاعة
    cap = scene.get("caption", "")
    cap_y = py0 + ph_h + 34
    if cap:
        f_cap = font("ar", 46)
        txt = shape(cap)
        cw, ch, _ = measure(d, txt, f_cap)
        bw2 = min(W - 160, cw + 90)
        card(frame, (W / 2 - bw2 / 2, cap_y, W / 2 + bw2 / 2, cap_y + ch + 52),
             radius=32, fill=WHITE, w=6, shadow=8)
        d = ImageDraw.Draw(frame)
        text_center(d, W / 2, cap_y + (ch + 52) / 2, txt, f_cap, BLUE_DARK)
        cap_y += ch + 82

    # --- اللوحة (تحت)
    bx0, bx1 = 70, W - 70
    by0, by1 = cap_y + 10, H - 150
    pop = max(0.06, ease_out_back(t / 0.40)) if t < 0.40 else 1.0
    bw, bh = (bx1 - bx0) * pop, (by1 - by0) * pop
    ccx, ccy = (bx0 + bx1) / 2, (by0 + by1) / 2
    card(frame, (ccx - bw / 2, ccy - bh / 2, ccx + bw / 2, ccy + bh / 2),
         radius=48, fill=WHITE, w=8, shadow=14)
    d = ImageDraw.Draw(frame)

    if pop > 0.85:
        f_bt = font("ar", 46)
        bt = shape(scene.get("board_title", ""))
        yy = by0 + 30
        if bt:
            tw2, th2, _ = measure(d, bt, f_bt)
            pad = 28
            d.rounded_rectangle((ccx - tw2 / 2 - pad, yy,
                                 ccx + tw2 / 2 + pad, yy + th2 + 26),
                                26, fill=TEAL)
            text_center(d, ccx, yy + (th2 + 26) / 2, bt, f_bt, WHITE)
            yy += th2 + 60

        lines = scene.get("lines", [])
        slot = (by1 - 40 - yy) / max(1, len(lines))
        for i, ln in enumerate(lines):
            if "reveal_at" in ln:
                start = ln["reveal_at"] * dur
            else:
                start = 0.5 + i * 0.55
            p = ease_out((t - start) / 0.45)
            if p <= 0:
                continue
            style = ln.get("style", "eq")
            col, size = STYLE.get(style, STYLE["eq"])
            kind = "ar" if AR_RE.search(ln["text"]) else "num"
            txt = shape(ln["text"])
            f_eq = font_fit(d, kind, int(size * (0.9 + 0.1 * p)), txt,
                            (bx1 - bx0) - 110)
            y = yy + slot * (i + 0.5) + (1 - p) * 36
            w_, h_, b_ = measure(d, txt, f_eq)
            x_ = ccx - w_ / 2 - b_[0]
            d.text((x_ + 4, y - h_ / 2 - b_[1] + 4), txt, font=f_eq,
                   fill=(0, 0, 0, int(40 * p)))
            d.text((x_, y - h_ / 2 - b_[1]), txt, font=f_eq, fill=col)
            if style == "answer":
                pr = ease_out((t - (start + 0.5)) / 0.7)
                if pr > 0:
                    hand_ellipse(d, (ccx - w_ / 2 - 55, y - h_ / 2 - 40,
                                     ccx + w_ / 2 + 55, y + h_ / 2 + 40),
                                 CORAL, pr, width=10, seed=idx + 2)

    if scene.get("confetti"):
        rnd = random.Random(99)
        for i in range(80):
            sx = rnd.randint(0, W)
            sp = rnd.uniform(180, 430)
            delay = rnd.uniform(0, 0.9)
            yy2 = -60 + (t - delay) * sp
            if yy2 < -60 or yy2 > H:
                continue
            c = [CORAL, SUN, BLUE, GREEN, VIOLET][i % 5]
            s = rnd.randint(10, 22)
            ang = (t * 240 + i * 37) % 360
            k = abs(math.cos(math.radians(ang)))
            d.rectangle((sx, yy2, sx + s * (0.3 + k), yy2 + s * 0.6), fill=c)

    f_b = font("ar", 38)
    text_center(d, W / 2, H - 66, shape(cfg.get("brand", "")), f_b, BLUE_DARK)
    return frame.convert("RGB")


# ------------------------------------------------- موسيقى خلفية هادئة ------
def make_bgm(path, total_dur, sr=44100):
    """يولّد مقطع موسيقي خافت (أرپيجيو بيانو ناعم) بطول الفيديو — بلا ملفات خارجية."""
    import struct
    import wave
    # سلّم بنتاتوني C ماجور — دايماً متناغم
    freqs = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
    rnd = random.Random(42)
    n = int(total_dur * sr)
    buf = [0.0] * n
    beat = 0.5                                   # نوطة كل نصف ثانية
    t0 = 0.0
    step = 0
    while t0 < total_dur:
        f0 = freqs[(step * 2 + rnd.randint(0, 1)) % len(freqs)]
        if step % 8 == 0:
            f0 = freqs[0]                        # نرجعو للجذر
        dur_n = beat * rnd.choice([1, 1, 2])
        a, b = int(t0 * sr), min(n, int((t0 + dur_n) * sr))
        for i in range(a, b):
            tt = (i - a) / sr
            env = math.exp(-tt * 3.2) * min(1.0, tt * 60)
            v = (math.sin(2 * math.pi * f0 * tt) * 0.7 +
                 math.sin(2 * math.pi * f0 * 2 * tt) * 0.2 +
                 math.sin(2 * math.pi * f0 * 0.5 * tt) * 0.25)
            buf[i] += v * env * 0.16
        t0 += beat
        step += 1
    # fade in / out
    fade = int(1.2 * sr)
    for i in range(min(fade, n)):
        buf[i] *= i / fade
        buf[n - 1 - i] *= i / fade
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
            for s in buf))


# ------------------------------------------------------------ الصوت --------
def audio_duration(path):
    out = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if not m:
        return 4.0
    h, mm, s = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(s)


# ------------------------------------------------------------ الترجمة ------
def fmt_ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


def write_srt(scenes, durs, path, offset0=0.0):
    """يولّد ملف ترجمة SRT من نصوص narration (جملة جملة حسب الطول)."""
    cues = []
    offset = offset0
    for sc, dur in zip(scenes, durs):
        txt = sc.get("narration", "").strip()
        if txt:
            parts = [p.strip() for p in re.split(r"(?<=[.!؟?…])\s+", txt) if p.strip()]
            total_chars = sum(len(p) for p in parts) or 1
            t0 = offset
            for p in parts:
                share = dur * len(p) / total_chars
                cues.append((t0, min(t0 + share, offset + dur), p))
                t0 += share
        offset += dur
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (i, fmt_ts(a), fmt_ts(b), txt))


# ------------------------------------------------------------- التشغيل -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--tail", type=float, default=0.7)
    ap.add_argument("--bgm", action="store_true",
                    help="موسيقى خلفية هادئة متولّدة أوتوماتيكياً")
    ap.add_argument("--bgm-vol", type=float, default=0.30)
    ap.add_argument("--intro", action="store_true",
                    help="جينيريك مقدمة 3.2 ثانية باللوغو")
    args = ap.parse_args()

    cfg = json.load(open(args.scenes, encoding="utf-8"))
    W, H, FPS = cfg["width"], cfg["height"], cfg["fps"]
    scenes = cfg["scenes"]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    durs, audios = [], []
    for sc in scenes:
        ap_ = os.path.join(HERE, sc["audio"]) if sc.get("audio") else None
        if ap_ and os.path.exists(ap_) and not args.no_audio:
            durs.append(audio_duration(ap_) + args.tail)
            audios.append(ap_)
        else:
            durs.append(sc.get("duration", 4.0))
            audios.append(None)

    bg = make_background(W, H)
    intro_dur = 3.2 if args.intro else 0.0

    silent = args.out + ".silent.mp4"
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_frames = sum(int(d * FPS) for d in durs) + int(intro_dur * FPS)
    done = 0
    if intro_dur:
        n = int(intro_dur * FPS)
        for f in range(n):
            t = f / FPS
            img = draw_intro(cfg, t, intro_dur, bg)
            proc.stdin.write(img.tobytes())
            done += 1
    for i, (sc, dur) in enumerate(zip(scenes, durs)):
        n = int(dur * FPS)
        for f in range(n):
            t = f / FPS
            img = draw_frame(cfg, sc, t, dur, bg, i, len(scenes))
            proc.stdin.write(img.tobytes())
            done += 1
            if done % 60 == 0:
                sys.stdout.write("\r  %d/%d (%d%%)" %
                                 (done, total_frames, 100 * done // total_frames))
                sys.stdout.flush()
    proc.stdin.close()
    proc.wait()
    print("\r  video ok" + " " * 20)

    # SRT (مزاح بمدة الجينيريك)
    srt = os.path.splitext(args.out)[0] + ".srt"
    write_srt(scenes, durs, srt, offset0=intro_dur)

    if args.no_audio or not any(audios):
        os.replace(silent, args.out)
        print("out:", args.out)
        return

    inputs, filters, labels = [], [], []
    offset, k = intro_dur, 0
    total_dur = sum(durs) + intro_dur
    for a, dur in zip(audios, durs):
        if a:
            inputs += ["-i", a]
            k += 1
            filters.append("[%d:a]adelay=%d:all=1,apad=whole_dur=%f[a%d]"
                           % (k, int(offset * 1000), total_dur, k))
            labels.append("[a%d]" % k)
        offset += dur

    bgm_path = None
    if args.bgm:
        bgm_path = args.out + ".bgm.wav"
        make_bgm(bgm_path, total_dur)
        inputs += ["-i", bgm_path]
        k += 1
        filters.append("[%d:a]volume=%f[a%d]" % (k, args.bgm_vol, k))
        labels.append("[a%d]" % k)

    mix = "".join(labels) + "amix=inputs=%d:normalize=0[aout]" % len(labels)
    cmd = ([FFMPEG, "-y", "-i", silent] + inputs +
           ["-filter_complex", ";".join(filters) + ";" + mix,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", args.out])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    os.remove(silent)
    if bgm_path and os.path.exists(bgm_path):
        os.remove(bgm_path)
    print("out:", args.out, "dur=%.1fs" % sum(durs))


if __name__ == "__main__":
    main()
