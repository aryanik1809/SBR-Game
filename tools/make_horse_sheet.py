#!/usr/bin/env python3
"""Tile the preview renders into one turnaround sheet (assets/horse/previews/sheet.png)."""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "assets", "horse", "previews")
NAMES = ["stand_three_q", "stand_side", "stand_front", "stand_back",
         "gallop_three_q", "gallop_side", "stand_head", "stand_saddle"]
T = 600
sheet = Image.new("RGB", (T * 4, T * 2))
for i, n in enumerate(NAMES):
    im = Image.open(os.path.join(D, n + ".png")).convert("RGB").resize((T, T), Image.LANCZOS)
    sheet.paste(im, ((i % 4) * T, (i // 4) * T))
sheet.save(os.path.join(D, "sheet.png"), optimize=True)
print("wrote sheet.png")
