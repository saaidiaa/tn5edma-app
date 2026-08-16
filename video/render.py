#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py — يحوّل معادلات رياضية إلى فيديو كرتوني عمودي (Reels / TikTok / Shorts).

الاستعمال:
    python3 render.py                      # يقرأ scenes.json ويخرج out/video.mp4
    python3 render.py --scenes myfile.json --out out/lesson2.mp4
    python3 render.py --no-audio           # معاينة سريعة بدون صوت

المتطلبات:  pip install pillow arabic-reshaper python-bidi imageio-ffmpeg
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
    "/usr/local/lib/python3.11/dist-packages/matplotlib/mpl-data/fonts/ttf",
    "/usr/share/fonts/truetype/dejavu",
]
FONT_CANDIDATES = {
    "ar":     ["Cairo.ttf", "NotoSansArabic.ttf", "Amiri-Bold.ttf", "DejaVuSans-Bold.ttf"],
    "ar_reg": ["Cairo.ttf", "NotoSansArabic.ttf", "DejaVuSans.ttf"],
    "math":   ["PatrickHand.ttf", "DejaVuSans-Bold.ttf"],
}


def _find(names):
    for n in names:
        for d in FONT_DIRS:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    raise RuntimeError("ما لقيتش خط مناسب: " + ", ".join(names))


_FONT_CACHE = {}


def font(kind, size):
    key = (kind, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(_find(FONT_CANDIDATES[kind]), size)
    return _FONT_CACHE[key]


AR_RE = re.compile(r"[\u0600-\u06FF]")


def shape(txt):
    """تشكيل النص العربي (وصل الحروف + اتجاه RTL)."""
    if HAS_AR and AR_RE.search(txt):
        return get_display(arabic_reshaper.reshape(txt))
    return txt


# ---------------------------------------------------------------- الألوان ---
PAPER      = (253, 248, 236)
GRID       = (232, 223, 203)
INK        = (32, 36, 46)
TEAL       = (23, 145, 148)
TEAL_DARK  = (13, 105, 108)
CORAL      = (240, 92, 84)
SUN        = (255, 197, 61)
GREEN      = (46, 179, 105)
VIOLET     = (124, 92, 214)
WHITE      = (255, 255, 255)

STYLE_COLOR = {"eq": INK, "op": CORAL, "ask": VIOLET, "answer": GREEN}


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


def text_center(draw, cx, cy, txt, fnt, fill, outline=None, ow=6):
    w, h, b = measure(draw, txt, fnt)
    x, y = cx - w / 2 - b[0], cy - h / 2 - b[1]
    if outline:
        draw.text((x, y), txt, font=fnt, fill=outline,
                  stroke_width=ow, stroke_fill=outline)
    draw.text((x, y), txt, font=fnt, fill=fill)
    return w, h


def cartoon_box(img, box, radius=48, fill=WHITE, line=INK, w=8, shadow=14):
    """مستطيل كرتوني: ظل صلب + حدود سميكة."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    if shadow:
        d.rounded_rectangle((x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow),
                            radius, fill=INK)
    d.rounded_rectangle(box, radius, fill=fill, outline=line, width=w)


def make_background(W, H, seed=7):
    """ورقة كرّاس بخطوط شبكة + خربشات رياضية باهتة."""
    bg = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(bg)
    step = 60
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=GRID, width=2)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=GRID, width=2)

    rnd = random.Random(seed)
    doodles = ["+", "−", "×", "÷", "=", "π", "√", "x", "y", "%", "∑", "∞"]
    faint = (225, 214, 192)
    for _ in range(26):
        f = font("math", rnd.randint(46, 110))
        d.text((rnd.randint(-20, W - 40), rnd.randint(-20, H - 60)),
               rnd.choice(doodles), font=f, fill=faint)
    # هالة لونية فوق و تحت
    top = Image.new("RGB", (W, H), TEAL)
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-W * 0.4, -H * 0.22, W * 1.4, H * 0.20), fill=60)
    md.ellipse((-W * 0.4, H * 0.86, W * 1.4, H * 1.25), fill=45)
    bg = Image.composite(top, bg, mask.filter(ImageFilter.GaussianBlur(90)))
    return bg


def load_mascot(name, height):
    """يحمّل صورة الشخصية و يشيل الخلفية البيضاء."""
    p = os.path.join(HERE, "assets", "mascot_%s.png" % name)
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > 238 and g > 238 and b > 238:
                px[x, y] = (r, g, b, 0)
            elif r > 224 and g > 224 and b > 224:
                px[x, y] = (r, g, b, 90)
    # قصّ الفراغ
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    ratio = height / im.height
    return im.resize((max(1, int(im.width * ratio)), height), Image.LANCZOS)


def paste_a(base, img, xy):
    base.alpha_composite(img, xy) if base.mode == "RGBA" else base.paste(img, xy, img)


def hand_ellipse(draw, box, color, progress, width=9, seed=3):
    """دائرة مرسومة باليد تتكوّن تدريجياً حوالي الجواب."""
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


def speech_bubble(img, box, txt, fnt, tail_x):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 + 8, y0 + 8, x1 + 8, y1 + 8), 36, fill=INK)
    d.rounded_rectangle(box, 36, fill=WHITE, outline=INK, width=7)
    d.polygon([(tail_x, y1 - 4), (tail_x + 46, y1 - 4), (tail_x + 14, y1 + 46)],
              fill=WHITE, outline=INK)
    d.line([(tail_x, y1 - 4), (tail_x + 14, y1 + 46), (tail_x + 46, y1 - 4)],
           fill=INK, width=7)
    text_center(d, (x0 + x1) / 2, (y0 + y1) / 2, txt, fnt, INK)


# ------------------------------------------------------------- الإطار ------
def draw_frame(cfg, scene, t, dur, bg, mascots, idx, total):
    W, H = cfg["width"], cfg["height"]
    frame = bg.copy().convert("RGBA")
    d = ImageDraw.Draw(frame)

    # --- شريط العنوان العلوي
    f_brand = font("ar", 46)
    chip_w = int(W * 0.74)
    cartoon_box(frame, ((W - chip_w) // 2, 70, (W + chip_w) // 2, 190),
                radius=60, fill=SUN, w=7, shadow=10)
    d = ImageDraw.Draw(frame)
    text_center(d, W / 2, 130, shape(cfg.get("title", "")), f_brand, INK)

    # --- مؤشّر تقدّم الخطوات
    dot_r, gap = 13, 46
    tot_w = total * gap
    for i in range(total):
        cx = W / 2 - tot_w / 2 + gap / 2 + i * gap
        col = TEAL if i <= idx else (215, 208, 191)
        d.ellipse((cx - dot_r, 222 - dot_r, cx + dot_r, 222 + dot_r),
                  fill=col, outline=INK, width=4)

    # --- اللوحة
    bx0, bx1 = 80, W - 80
    by0, by1 = 300, 300 + 660
    pop = max(0.06, ease_out_back(t / 0.40)) if t < 0.40 else 1.0
    bw, bh = (bx1 - bx0) * pop, (by1 - by0) * pop
    ccx, ccy = (bx0 + bx1) / 2, (by0 + by1) / 2
    board = (ccx - bw / 2, ccy - bh / 2, ccx + bw / 2, ccy + bh / 2)
    cartoon_box(frame, board, radius=54, fill=WHITE, w=9, shadow=16)
    d = ImageDraw.Draw(frame)

    if pop > 0.85:
        # عنوان صغير داخل اللوحة
        f_bt = font("ar", 44)
        bt = shape(scene.get("board_title", ""))
        if bt:
            tw, th, _ = measure(d, bt, f_bt)
            pad = 26
            d.rounded_rectangle((ccx - tw / 2 - pad, by0 + 34,
                                 ccx + tw / 2 + pad, by0 + 34 + th + 26),
                                26, fill=TEAL)
            text_center(d, ccx, by0 + 34 + (th + 26) / 2, bt, f_bt, WHITE)

        # أسطر المعادلة (ظهور متدرّج)
        lines = scene.get("lines", [])
        base_y = by0 + 210
        slot = (by1 - 60 - base_y) / max(1, len(lines))
        for i, ln in enumerate(lines):
            start = 0.55 + i * 0.55
            p = ease_out((t - start) / 0.45)
            if p <= 0:
                continue
            style = ln.get("style", "eq")
            size = 118 if style in ("eq", "answer") else 92
            f_eq = font("math", int(size * (0.9 + 0.1 * p)))
            col = STYLE_COLOR.get(style, INK)
            y = base_y + slot * (i + 0.5) + (1 - p) * 40
            txt = shape(ln["text"])
            # ظل نصّي كرتوني
            w_, h_, b_ = measure(d, txt, f_eq)
            x_ = ccx - w_ / 2 - b_[0]
            d.text((x_ + 5, y - h_ / 2 - b_[1] + 5), txt, font=f_eq,
                   fill=(0, 0, 0, int(45 * p)))
            d.text((x_, y - h_ / 2 - b_[1]), txt, font=f_eq, fill=col)

            if style == "answer":
                pr = ease_out((t - (start + 0.5)) / 0.7)
                if pr > 0:
                    hand_ellipse(d, (ccx - w_ / 2 - 60, y - h_ / 2 - 46,
                                     ccx + w_ / 2 + 60, y + h_ / 2 + 46),
                                 CORAL, pr, width=10, seed=idx + 2)

    # --- الشخصية (تهزّ بلطف)
    m = mascots.get(scene.get("mascot", "explain"))
    if m:
        bob = int(math.sin(t * 3.1) * 12)
        entry = ease_out_back(t / 0.5) if t < 0.5 else 1.0
        mx = int(W - m.width - 40)
        my = int(H - m.height - 300 + bob + (1 - entry) * 220)
        frame.alpha_composite(m, (mx, my))

    # --- فقاعة الكلام / الترجمة
    cap = scene.get("caption", "")
    if cap:
        f_cap = font("ar", 52)
        txt = shape(cap)
        tw, th, _ = measure(d, txt, f_cap)
        bw2 = min(W - 140, tw + 90)
        y1 = H - 250
        y0 = y1 - (th + 80)
        speech_bubble(frame, ((W - bw2) / 2, y0, (W + bw2) / 2, y1),
                      txt, f_cap, tail_x=W - 330)
        d = ImageDraw.Draw(frame)

    # --- كونفيتي في مشهد الخاتمة
    if scene.get("confetti"):
        rnd = random.Random(99)
        for i in range(70):
            sx = rnd.randint(0, W)
            sp = rnd.uniform(180, 420)
            delay = rnd.uniform(0, 0.9)
            yy = -60 + (t - delay) * sp
            if yy < -60 or yy > H:
                continue
            c = [CORAL, SUN, TEAL, GREEN, VIOLET][i % 5]
            s = rnd.randint(10, 22)
            ang = (t * 240 + i * 37) % 360
            k = abs(math.cos(math.radians(ang)))
            d.rectangle((sx, yy, sx + s * (0.3 + k), yy + s * 0.6), fill=c)

    # --- العلامة التجارية أسفل
    f_b = font("ar_reg", 38)
    text_center(d, W / 2, H - 90, shape(cfg.get("brand", "")), f_b, TEAL_DARK)
    return frame.convert("RGB")


# ------------------------------------------------------------ الصوت --------
def audio_duration(path):
    out = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if not m:
        return 4.0
    h, mm, s = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(s)


# ------------------------------------------------------------- التشغيل -----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=os.path.join(HERE, "scenes.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out", "video.mp4"))
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--tail", type=float, default=0.6, help="فراغ بعد كل مشهد (ثانية)")
    args = ap.parse_args()

    cfg = json.load(open(args.scenes, encoding="utf-8"))
    W, H, FPS = cfg["width"], cfg["height"], cfg["fps"]
    scenes = cfg["scenes"]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    # مدّة كل مشهد = مدّة تعليقه الصوتي
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
    mascots = {n: load_mascot(n, 620) for n in ("explain", "happy", "think")}

    silent = os.path.join(HERE, "out", "_silent.mp4")
    proc = subprocess.Popen(
        [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", silent],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    total_frames = sum(int(d * FPS) for d in durs)
    done = 0
    for i, (sc, dur) in enumerate(zip(scenes, durs)):
        n = int(dur * FPS)
        for f in range(n):
            t = f / FPS
            img = draw_frame(cfg, sc, t, dur, bg, mascots, i, len(scenes))
            proc.stdin.write(img.tobytes())
            done += 1
            if done % 30 == 0:
                sys.stdout.write("\r  🎬 %d/%d إطار (%d%%)"
                                 % (done, total_frames, 100 * done // total_frames))
                sys.stdout.flush()
    proc.stdin.close()
    proc.wait()
    print("\r  ✅ الفيديو الصامت جاهز%s" % (" " * 20))

    if args.no_audio or not any(audios):
        os.replace(silent, args.out)
        print("📼", args.out)
        return

    # تركيب الصوت: كل تعليق يبدأ في بداية مشهده
    inputs, filters, labels = [], [], []
    offset = 0.0
    k = 0
    total_dur = sum(durs)
    for a, dur in zip(audios, durs):
        if a:
            inputs += ["-i", a]
            k += 1                       # مؤشّر المدخل في ffmpeg (0 = الفيديو)
            filters.append("[%d:a]adelay=%d:all=1,apad=whole_dur=%f[a%d]"
                           % (k, int(offset * 1000), total_dur, k))
            labels.append("[a%d]" % k)
        offset += dur

    mix = "".join(labels) + "amix=inputs=%d:normalize=0[aout]" % len(labels)
    cmd = ([FFMPEG, "-y", "-i", silent] + inputs +
           ["-filter_complex", ";".join(filters) + ";" + mix,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", args.out])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    os.remove(silent)
    print("📼 جاهز:", args.out, "| المدّة ≈ %.1f ثانية" % sum(durs))


if __name__ == "__main__":
    main()
