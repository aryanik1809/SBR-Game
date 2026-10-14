#!/usr/bin/env python3
"""A second original theme in the same Western / Steel Ball Run mood: `theme_dust` (assets/audio/theme_dust.ogg).

    python3 tools/make_theme_dust.py

New tune, new key and tempo (D minor, 132 BPM, against the first theme's E minor / 120), same palette: brass,
spaghetti-western guitar, choir, timpani and a galloping rhythm. Reuses the instruments in make_audio.py.

Form (32 bars, ~58 s, loops):  intro 4 | verse 8 | chorus 8 | bridge 4 | final chorus 8
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_audio as ma  # noqa: E402
from make_audio import Mix, n_, ns, SR  # noqa: E402

ma.BPM = 132
ma.BEAT = 60 / ma.BPM
ma.BAR = ma.BEAT * 4
ma.CHORDS.update({
    "Dm": dict(bass=38, pcs={2, 5, 9}, pad=[50, 53, 57, 62], pow=50),
    "Bb": dict(bass=34, pcs={10, 2, 5}, pad=[46, 53, 58, 62], pow=46),
    "F": dict(bass=41, pcs={5, 9, 0}, pad=[48, 53, 57, 60], pow=53),
    "C5": dict(bass=36, pcs={0, 4, 7}, pad=[48, 52, 55, 60], pow=48),
    "Gm": dict(bass=43, pcs={7, 10, 2}, pad=[50, 55, 58, 62], pow=43),
    "A": dict(bass=33, pcs={9, 1, 4}, pad=[45, 52, 57, 61], pow=45),
})

CHORUS = [  # (chord, [(beat, dur, note)])
    ("Dm", [(0, 1, "A4"), (1, .5, "D5"), (1.5, .5, "E5"), (2, 1.5, "F5"), (3.5, .5, "E5")]),
    ("Bb", [(0, 1, "D5"), (1, 1, "F5"), (2, 1.5, "G5"), (3.5, .5, "F5")]),
    ("F", [(0, 1.5, "A5"), (1.5, .5, "G5"), (2, 1, "F5"), (3, 1, "C5")]),
    ("C5", [(0, 2, "E5"), (2, 1, "D5"), (3, 1, "C5")]),
    ("Dm", [(0, 1, "A4"), (1, .5, "D5"), (1.5, .5, "E5"), (2, 1.5, "F5"), (3.5, .5, "A5")]),
    ("Gm", [(0, 1, "G5"), (1, 1, "Bb5"), (2, 1.5, "A5"), (3.5, .5, "G5")]),
    ("A", [(0, 1, "C#5"), (1, 1, "E5"), (2, 2, "A5")]),
    ("A", [(0, 1, "G5"), (1, 1, "E5"), (2, 2, "C#5")]),
]
VERSE_LEAD = [
    ("Dm", [(0, .5, "D4"), (.5, .5, "F4"), (1, 1, "A4"), (2, .5, "G4"), (2.5, .5, "F4"), (3, 1, "D4")]),
    ("Dm", [(0, .5, "D4"), (.5, .5, "E4"), (1, 1, "F4"), (2, .5, "E4"), (2.5, .5, "D4"), (3, 1, "C#4")]),
    ("Gm", [(0, .5, "G4"), (.5, .5, "Bb4"), (1, 1, "D5"), (2, .5, "C5"), (2.5, .5, "Bb4"), (3, 1, "G4")]),
    ("A", [(0, .5, "A4"), (.5, .5, "C#5"), (1, 1, "E5"), (2, 2, "C#5")]),
]
VERSE = ["Dm", "Dm", "Bb", "C5", "Dm", "Dm", "Gm", "A"]


def verse(mx, t0, level=1.0):
    BAR, BEAT = ma.BAR, ma.BEAT
    for i, ch in enumerate(VERSE):
        bt = t0 + i * BAR
        ma.guitar_gallop(mx, bt, ch, level)
        ma.bass_gallop(mx, bt, ch, level)
        ma.drums_gallop(mx, bt, level, fill=(i == 7), crash_on=(i == 0))
        if i in (2, 3, 6):  # brass stabs answer the riff
            hits = [(2.5, "A4"), (3, "D5"), (3.5, "F5")] if i != 6 else [(2.5, "G4"), (3, "Bb4"), (3.5, "D5")]
            for beat, name in hits:
                m = n_(name)
                mx.add(ma.brass(m, 0.22, 0.9), bt + beat * BEAT, 0.85, pan=-0.1, send=0.3)
                mx.add(ma.brass(m - 5, 0.22, 0.6), bt + beat * BEAT, 0.7, pan=0.15, send=0.3)
    for i, (ch, notes) in enumerate(VERSE_LEAD):  # solo guitar line over the second half
        bt = t0 + (4 + i) * BAR
        for beat, dur, name in notes:
            mx.add(ma.pluck(n_(name) + 12, dur * BEAT, 0.8, bright=0.7, g=0.9985), bt + beat * BEAT, 0.55, pan=0.3, send=0.25)
    ma.pad_chord(mx, t0 + 4 * BAR, "Dm", 2, 0.5 * level)


def chorus(mx, t0, level=1.0, final=False):
    BAR, BEAT = ma.BAR, ma.BEAT
    for i, (ch, notes) in enumerate(CHORUS):
        bt = t0 + i * BAR
        if final:
            ma.guitar_strum(mx, bt, ch, True, 1.0, BAR)
            for b in (0.75, 1.5, 2.75, 3.5):
                ma.guitar_strum(mx, bt + b * BEAT, ch, b in (1.5, 3.5), 0.8, BEAT)
        else:
            ma.guitar_gallop(mx, bt, ch, 0.9 * level)
        ma.bass_gallop(mx, bt, ch, level)
        ma.drums_gallop(mx, bt, level, fill=(i in (3, 7)), crash_on=(i == 0 or (final and i == 4)))
        ma.pad_chord(mx, bt, ch, 1, 0.9 * level, choir_=True)
        ma.play_melody(mx, bt, notes, ch, level, harmony=final)
        if final:
            for beat, dur, name in notes:
                mx.add(ma.brass(n_(name) - 12, dur * BEAT * 0.95, 0.7), bt + beat * BEAT, 0.8, pan=0.05, send=0.3)
        if i % 2 == 0:
            mx.add(ma.timp(ma.CHORDS[ch]["bass"] + 12, 1.2, 0.8), bt, 0.5, send=0.3)


def bridge(mx, t0, level=1.0):
    """Choir, bells and a heartbeat that builds into the last chorus."""
    BAR, BEAT = ma.BAR, ma.BEAT
    for i, ch in enumerate(["Gm", "Gm", "A", "A"]):
        bt = t0 + i * BAR
        ma.pad_chord(mx, bt, ch, 1, 1.0, choir_=True)
        mx.add(ma.bass_note(ma.CHORDS[ch]["bass"], BAR * 0.95, 0.9), bt, 0.9)
        for b in range(4):
            mx.add(ma.kick(0.55 + 0.1 * i), bt + b * BEAT, 0.5)
        notes = ("D5", "C5", "Bb4", "G4") if i < 2 else ("E5", "C#5", "A4", "E4")
        for k, name in enumerate(notes):
            mx.add(ma.bell(n_(name), 2.0, 0.9), bt + k * BEAT, 0.6, pan=-0.3 + 0.2 * k, send=0.5)
    ma.snare_roll(mx, t0 + 2 * BAR, 2 * BAR, 0.1, 1.0)
    ma.timp_roll(mx, t0 + 3 * BAR, BAR, 38 + 12, 0.3, 1.0)
    mx.add(ma.riser(4 * BAR, 0.9), t0, 0.7, send=0.3)


def intro(mx, t0):
    BAR, BEAT = ma.BAR, ma.BEAT
    for m in (26, 38, 45):
        mx.add(ma.pad_saw(m, 2 * BAR + 0.5, 1.0, att=1.5, rel=0.8, cutoff=500), t0, 0.9, send=0.5)
    for b in range(8):
        mx.add(ma.timp(38, 1.0, 0.45 + 0.05 * b), t0 + b * BEAT, 0.6, send=0.4)
    mx.add(ma.bell(n_("D5"), 4.0, 1.0), t0 + 2 * BAR - 0.02, 0.7, pan=-0.2, send=0.7)
    mx.add(ma.bell(n_("A5"), 4.0, 0.8), t0 + 2 * BAR + BEAT, 0.6, pan=0.25, send=0.7)
    for m in (38, 45, 50, 53):
        mx.add(ma.choir(m + 12, 2 * BAR, 0.55, att=1.2), t0 + 2 * BAR, 0.9, pan=(m % 5 - 2) * 0.2, send=0.6)
    ma.timp_roll(mx, t0 + 2 * BAR, 2 * BAR - 0.05, 38, 0.15, 1.0)
    ma.snare_roll(mx, t0 + 3 * BAR - 0.05, BAR, 0.1, 1.0, 0.1, 0.028)
    mx.add(ma.riser(2 * BAR, 0.9), t0 + 2 * BAR, 0.8, send=0.3)
    for k, name in enumerate(("A4", "D5", "F5")):
        mx.add(ma.brass(n_(name), 0.17, 1.0), t0 + 4 * BAR - BEAT + k * BEAT / 3, 0.9, send=0.3)


def hit_in(mx, t):
    for m in (n_("D3"), n_("A3"), n_("D4"), n_("F4"), n_("A4"), n_("D5")):
        mx.add(ma.brass(m, ma.BEAT * 1.6, 1.0), t, 0.55, pan=(m % 7 - 3) * 0.1, send=0.35)
    mx.add(ma.timp(38, 1.6, 1.0), t, 1.0, send=0.4)


def build():
    BAR = ma.BAR
    L = 32 * BAR
    mx = Mix(L + 6)
    intro(mx, 0)
    hit_in(mx, 4 * BAR)
    verse(mx, 4 * BAR, 0.98)
    chorus(mx, 12 * BAR, 1.0)
    bridge(mx, 20 * BAR, 1.0)
    chorus(mx, 24 * BAR, 1.05, final=True)
    return ma.finalize_music(mx, L)


def main():
    x = build()
    ma.write_ogg("theme_dust", x)
    import numpy as np
    print(f"theme_dust: {len(x) / SR:.1f}s peak {np.max(np.abs(x)):.2f} rms {np.sqrt(np.mean(x ** 2)):.3f}")
    mp = os.path.join(ma.OUT, "manifest.json")
    man = json.load(open(mp)) if os.path.exists(mp) else {}
    man["theme_dust"] = dict(kind="music", loop=True, volume=0.45, seconds=round(len(x) / SR, 2), file="theme_dust.ogg")
    with open(mp, "w") as f:
        json.dump(man, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
