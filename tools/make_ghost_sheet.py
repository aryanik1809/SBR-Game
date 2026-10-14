#!/usr/bin/env python3
"""Tile the ghost preview renders into a turnaround + close-up sheet (assets/ghost/previews/sheet.png)."""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "assets", "ghost", "previews")
TOP = ["front", "three_q", "side", "back", "three_q_back"]
BOTTOM = ["face", "hand", "zip"]
T = 520
sheet = Image.new("RGB", (T * 5, T * 2), (222, 214, 196))
for row, names in enumerate((TOP, BOTTOM)):
    for i, n in enumerate(names):
        im = Image.open(os.path.join(D, f"ghost_{n}.png")).convert("RGB")
        if row == 0:  # tighten on the figure
            w, h = im.size
            im = im.crop((int(w * 0.17), int(h * 0.12), int(w * 0.83), int(h * 0.92)))
        im.thumbnail((T, T), Image.LANCZOS)
        sheet.paste(im, (i * T + (T - im.width) // 2, row * T + (T - im.height) // 2))
sheet.save(os.path.join(D, "sheet.png"), optimize=True)
print("wrote sheet.png", sheet.size)
