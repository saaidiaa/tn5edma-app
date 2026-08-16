#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_shorts.py — يولّد نسخة Short عمودية (1080×1920) من أقوى مشهد في كل حلقة.

يقرأ ملف الحلقة، يختار المشاهد المحددة، يقلب الأبعاد لـ 9:16،
ويستدعي render_t3.py. الناتج: out/shorts/<id>_short.mp4

الاستعمال:  python3 make_shorts.py
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# لكل حلقة: المشاهد المختارة للـ Short (الأكثر جذبا)
SHORTS = {
    "ep1_numbers":        [1],       # عداد السيارة + تفكيك العدد
    "ep2_operations":     [0],       # مسألة السوق
    "ep3_geometry":       [2],       # محيط الجنان + كونفيتي
    "ep4_multiplication": [1],       # كويز الفران
    "ep5_respiration":    [2],       # كويز التلوث
    "ep6_circuit":        [1],       # تجربة الدارة
    "ep7_matter":         [2],       # كويز الغليان 100 درجة
    "ep8_grammar":        [2],       # كويز نوع الجملة
    "ep9_french":         [0],       # A comme Avion
}


def main():
    out_dir = os.path.join(HERE, "out", "shorts")
    os.makedirs(out_dir, exist_ok=True)
    for lid, idxs in SHORTS.items():
        cfg = json.load(open(os.path.join(HERE, "lessons", lid + ".json"),
                             encoding="utf-8"))
        cfg["width"], cfg["height"] = 1080, 1920
        cfg["scenes"] = [cfg["scenes"][i] for i in idxs]
        tmp = os.path.join(out_dir, "_%s.json" % lid)
        json.dump(cfg, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(out_dir, lid + "_short.mp4")
        print("== short:", lid)
        subprocess.run([sys.executable, os.path.join(HERE, "render_t3.py"),
                        "--scenes", tmp, "--out", out, "--bgm"], check=True)
        os.remove(tmp)


if __name__ == "__main__":
    main()
