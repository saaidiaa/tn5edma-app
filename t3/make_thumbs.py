#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_thumbs.py — يولّد صور مصغرة (Thumbnails) ليوتيوب 1280×720 لكل حلقة.

الوصفة: الصورة الواقعية كخلفية + تعتيم متدرّج + شارة EP حمراء +
العنوان بخط ضخم على لوحة صفراء + سطر ضخم بالأرقام اللاتينية (hook).

الاستعمال:  python3 make_thumbs.py
"""

import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_t3 as R

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1280, 720

# لكل حلقة: (ملف الدرس، الصورة، الـ hook الضخم بالأرقام اللاتينية)
THUMBS = [
    ("ep1_numbers",        "assets/img/ep1_odometer.jpg",  "99 999"),
    ("ep2_operations",     "assets/img/ep2_market.jpg",    "3 500 + 2 750"),
    ("ep3_geometry",       "assets/img/ep3_rails.jpg",     "P = 40 m"),
    ("ep4_multiplication", "assets/img/ep4_eggs.jpg",      "3 x 4 = ?"),
    ("ep5_respiration",    "assets/img/ep5_lungs.jpg",     "90 / min"),
    ("ep6_circuit",        "assets/img/ep6_battery.jpg",   "4.5 V"),
    ("ep7_matter",         "assets/img/ep7_steam.jpg",     "0 -> 100 °C"),
    ("ep8_grammar",        "assets/img/ep8_board.jpg",     "Quiz ?"),
    ("ep9_french",         "assets/img/ep9_letters.jpg",   "A B C"),
]


def make(lesson_id, img_rel, hook):
    cfg = json.load(open(os.path.join(HERE, "lessons", lesson_id + ".json"),
                         encoding="utf-8"))
    title = cfg["title"]
    ep = cfg.get("episode", "")

    # الخلفية = الصورة الواقعية مكبّرة + تعتيم من اليسار
    im = Image.open(os.path.join(HERE, img_rel)).convert("RGB")
    scale = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * scale) + 1, int(im.height * scale) + 1),
                   Image.LANCZOS)
    x = (im.width - W) // 2
    y = (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(0.4))

    grad = Image.new("L", (W, 1), 0)
    for gx in range(W):
        grad.putpixel((gx, 0), int(200 * max(0.0, 1 - gx / (W * 0.72))))
    grad = grad.resize((W, H))
    im = Image.composite(Image.new("RGB", (W, H), (10, 14, 26)), im, grad)

    d = ImageDraw.Draw(im)

    # شارة EP
    f_ep = R.font("num", 64)
    d.rounded_rectangle((44, 40, 264, 138), 30, fill=R.CORAL,
                        outline=(255, 255, 255), width=6)
    R.text_center(d, 154, 86, "EP %s" % ep, f_ep, R.WHITE)

    # العنوان على لوحة صفراء (سطران إذا طويل)
    words = title.split()
    lines, cur = [], ""
    for w_ in words:
        if len(cur) + len(w_) + 1 <= 18:
            cur = (cur + " " + w_).strip()
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    lines = lines[:2]

    f_t = R.font("ar", 76)
    ty = 210
    for ln in lines:
        txt = R.shape(ln)
        tw, th, _ = R.measure(d, txt, f_t)
        pad = 26
        d.rounded_rectangle((44, ty, 44 + tw + pad * 2, ty + th + 40), 22,
                            fill=R.SUN, outline=R.INK, width=6)
        R.text_center(d, 44 + pad + tw / 2, ty + (th + 40) / 2, txt, f_t, R.INK)
        ty += th + 66

    # الـ hook الضخم بالأرقام اللاتينية
    f_h = R.font("num", 130)
    hw, hh, hb = R.measure(d, hook, f_h)
    hx, hy = 60, H - hh - 110
    d.text((hx + 8, hy + 8), hook, font=f_h, fill=(0, 0, 0))
    d.text((hx, hy), hook, font=f_h, fill=(87, 255, 148),
           stroke_width=8, stroke_fill=(6, 40, 20))

    # شارة السلسلة
    f_b = R.font("ar", 40)
    bt = R.shape("السنة الثالثة أساسي")
    bw2, bh2, _ = R.measure(d, bt, f_b)
    d.rounded_rectangle((W - bw2 - 96, 44, W - 36, 44 + bh2 + 34), 26,
                        fill=R.BLUE, outline=(255, 255, 255), width=5)
    R.text_center(d, W - 36 - (bw2 + 60) / 2, 44 + (bh2 + 34) / 2, bt, f_b, R.WHITE)

    out = os.path.join(HERE, "out", "thumbs", lesson_id + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, quality=92)
    print("thumb:", out)


if __name__ == "__main__":
    for lid, img, hook in THUMBS:
        make(lid, img, hook)
