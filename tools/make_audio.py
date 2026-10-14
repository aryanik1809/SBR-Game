#!/usr/bin/env python3
"""Synthesise the SBR Game soundtrack and sound effects (no samples, no external assets).

    pip install numpy scipy soundfile
    python3 tools/make_audio.py              # writes assets/audio/*.ogg + manifest.json
    python3 tools/make_audio.py sfx          # only SFX
    python3 tools/make_audio.py music        # only music

Everything is generated from oscillators, filtered noise and Karplus-Strong strings, so the
music is an original piece "inspired by" the Western-meets-heroic-bombast feel of Steel Ball Run:
E minor / Phrygian-dominant colour, galloping triplet-ish rhythm, brass fanfares, timpani rolls,
strummed guitar and a choir pad.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio")
rng = np.random.default_rng(1890)
PI2 = 2 * np.pi


# ----------------------------------------------------------------------------
# DSP helpers
# ----------------------------------------------------------------------------
def ns(sec):
    return int(round(sec * SR))


def tt(n):
    return np.arange(n) / SR


def mtof(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=float) - 69) / 12)


def filt(x, kind, fc, order=2):
    fc = np.clip(fc, 20, SR / 2 - 200)
    sos = signal.butter(order, fc, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def band(x, lo, hi, order=2):
    lo, hi = np.clip(lo, 20, SR / 2 - 400), np.clip(hi, 40, SR / 2 - 200)
    sos = signal.butter(order, [lo, hi], btype="bandpass", fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def noise(n):
    return rng.uniform(-1, 1, n)


def interp_env(n, pts):
    """Piecewise-linear envelope from [(time_s, value), ...]."""
    t = tt(n)
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys)


def expd(n, tau):
    return np.exp(-tt(n) / tau)


def fit(x, n):
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def normalise(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def reverb_ir(rt60, seed, damp=5500, pre=0.012):
    r = np.random.default_rng(seed)
    n = ns(rt60)
    ir = r.normal(size=n) * np.exp(-6.9 * tt(n) / rt60)
    ir = filt(ir, "lowpass", damp, 1)
    ir[: ns(pre)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    return ir


def reverb(x, rt60=2.2, damp=5500):
    """x: (n, 2) -> stereo reverb tail of the same length."""
    out = np.zeros_like(x)
    for ch in range(2):
        ir = reverb_ir(rt60, 11 + ch, damp)
        out[:, ch] = signal.fftconvolve(x[:, ch], ir)[: len(x)]
    return out


class Mix:
    def __init__(self, seconds):
        self.n = ns(seconds)
        self.dry = np.zeros((self.n, 2))
        self.wet = np.zeros((self.n, 2))

    def add(self, sig, t, gain=1.0, pan=0.0, send=0.0):
        i = ns(t)
        if i >= self.n or len(sig) == 0:
            return
        seg = sig[: self.n - i] * gain
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        j = i + len(seg)
        self.dry[i:j, 0] += seg * l
        self.dry[i:j, 1] += seg * r
        if send:
            self.wet[i:j, 0] += seg * l * send
            self.wet[i:j, 1] += seg * r * send

    def render(self, rt60=2.4, wet_level=1.0):
        return self.dry + reverb(self.wet, rt60) * wet_level


def loop_wrap(x, length_samples):
    """Fold anything past `length_samples` back onto the start so the loop is seamless."""
    body = x[:length_samples].copy()
    tail = x[length_samples:]
    body[: len(tail)] += tail[: len(body)]
    return body


def write_ogg(name, x, quality=5):
    """Encode via ffmpeg/libvorbis (libsndfile's vorbis encoder crashes on long stereo files)."""
    import shutil
    import subprocess

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".ogg")
    tmp = os.path.join(OUT, f".{name}.tmp.wav")
    sf.write(tmp, np.clip(x, -1, 1).astype(np.float32), SR, subtype="PCM_16")
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-c:a", "libvorbis", "-q:a", str(quality), path],
                       check=True)
    else:  # fine for short mono clips
        sf.write(path, x.astype(np.float32), SR, format="OGG", subtype="VORBIS")
    os.remove(tmp)
    return path


# ----------------------------------------------------------------------------
# Instruments
# ----------------------------------------------------------------------------
def brass(m, dur, vel=1.0, vib=5.3, delay=0.15):
    f = float(mtof(m))
    n = ns(dur + 0.3)
    t = tt(n)
    vd = np.clip((t - delay) / 0.3, 0, 1) * 0.0055 * np.sin(PI2 * vib * t)
    ph = np.cumsum(f * (1 + vd)) / SR
    H = int(min(20, 9000 // f))
    bright = np.clip(0.50 + 0.46 * np.clip(t / 0.10, 0, 1), 0.3, 0.97)
    sig = np.zeros(n)
    for k in range(1, H + 1):
        sig += (k ** -0.72) * bright ** (k - 1) * np.sin(PI2 * k * ph)
    dur = max(dur, 0.16)
    env = np.interp(t, [0, 0.025, 0.12, dur, dur + 0.25], [0, 1, 0.82, 0.82, 0])
    chiff = filt(noise(n), "highpass", 1500, 1) * np.exp(-t / 0.035) * 0.10
    return (sig * env * 0.50 + chiff * env * 2.0) * vel


def choir(m, dur, vel=1.0, att=0.45, rel=0.9):
    f0 = float(mtof(m))
    n = ns(dur + rel)
    t = tt(n)
    out = np.zeros(n)
    for det in (-0.0045, 0.0, 0.0050):
        f = f0 * (1 + det)
        ph = np.cumsum(f * (1 + 0.0035 * np.sin(PI2 * 5.0 * t + det * 900))) / SR
        for k in range(1, int(min(28, 7000 // f)) + 1):
            hf = k * f
            w = (np.exp(-((hf - 780) / 330) ** 2) + 0.65 * np.exp(-((hf - 1180) / 420) ** 2)
                 + 0.18 * np.exp(-((hf - 2700) / 800) ** 2) + 0.30 / k)
            out += w / (k ** 0.4) * np.sin(PI2 * k * ph + k * det * 40)
    env = np.interp(t, [0, att, dur, dur + rel], [0, 1, 1, 0])
    return out * env * 0.11 * vel


def pad_saw(m, dur, vel=1.0, att=0.8, rel=1.2, cutoff=900):
    f = float(mtof(m))
    n = ns(dur + rel)
    t = tt(n)
    out = np.zeros(n)
    for det in (-0.006, 0.0, 0.006):
        ph = np.cumsum(np.full(n, f * (1 + det))) / SR
        out += 2 * (ph % 1.0) - 1
    out = filt(out, "lowpass", cutoff, 2)
    env = np.interp(t, [0, att, dur, dur + rel], [0, 1, 1, 0])
    return out * env * 0.12 * vel


def pluck(m, dur, vel=1.0, bright=0.55, g=0.997, drive=1.0):
    f = float(mtof(m))
    N = max(2, int(round(SR / f)))
    n = ns(dur + 0.12)
    exc = rng.uniform(-1, 1, N)
    # one-pole lowpass on the excitation for a softer pick
    exc = signal.lfilter([bright], [1, -(1 - bright)], exc)
    x = np.zeros(n)
    x[:N] = exc
    a = np.zeros(N + 2)
    a[0] = 1
    a[N] = -g / 2
    a[N + 1] = -g / 2
    y = signal.lfilter([1.0], a, x)
    y = filt(y, "highpass", 70, 1)
    # wooden body resonance
    y = y + 0.35 * band(y, 180, 260, 1) + 0.20 * band(y, 1800, 2600, 1)
    if drive > 1:
        y = softclip(y * 2.5, drive) * 0.5
    env = np.interp(tt(n), [0, dur, dur + 0.12], [1, 1, 0])
    return y * env * vel * 0.9


def bass_note(m, dur, vel=1.0):
    f = float(mtof(m))
    n = ns(dur + 0.1)
    t = tt(n)
    ph = np.cumsum(np.full(n, f)) / SR
    sig = np.sin(PI2 * ph) + 0.45 * np.sin(PI2 * 2 * ph + 0.3) + 0.22 * np.sin(PI2 * 3 * ph)
    sig *= np.exp(-t / (dur * 0.9 + 0.05))
    pick = filt(noise(n), "highpass", 900, 1) * np.exp(-t / 0.008) * 0.12
    env = np.interp(t, [0, 0.004, dur, dur + 0.1], [0, 1, 0.9, 0])
    return (sig * 0.5 + pick) * env * vel


def timp(m, dur=1.4, vel=1.0):
    f = float(mtof(m))
    n = ns(dur)
    t = tt(n)
    pitch = f * (1 + 0.28 * np.exp(-t / 0.045))
    ph = np.cumsum(pitch) / SR
    sig = np.sin(PI2 * ph) * np.exp(-t / 0.62) + 0.35 * np.sin(PI2 * 1.504 * ph) * np.exp(-t / 0.35)
    thump = filt(noise(n), "lowpass", 380, 2) * np.exp(-t / 0.025) * 0.9
    return (sig * 0.8 + thump) * vel


def kick(vel=1.0, n=None):
    n = n or ns(0.42)
    t = tt(n)
    f = 46 + 90 * np.exp(-t / 0.035)
    ph = np.cumsum(f) / SR
    sig = np.sin(PI2 * ph) * np.exp(-t / 0.16)
    click = filt(noise(n), "highpass", 2500, 1) * np.exp(-t / 0.004) * 0.25
    return softclip(sig * 1.3 + click, 1.2) * vel


def snare(vel=1.0):
    n = ns(0.3)
    t = tt(n)
    nz = band(noise(n), 1400, 7500, 2) * np.exp(-t / 0.075)
    tone = np.sin(PI2 * 188 * t) * np.exp(-t / 0.045) * 0.55 + np.sin(PI2 * 305 * t) * np.exp(-t / 0.03) * 0.25
    return (nz * 0.75 + tone) * vel


def snare_ghost(vel=0.4):
    return snare(vel)[: ns(0.12)] * np.linspace(1, 0.2, ns(0.12))


def tom(m, vel=1.0):
    f = float(mtof(m))
    n = ns(0.5)
    t = tt(n)
    ph = np.cumsum(f * (1 + 0.5 * np.exp(-t / 0.05))) / SR
    return (np.sin(PI2 * ph) * np.exp(-t / 0.20) + 0.2 * filt(noise(n), "lowpass", 900, 1) * np.exp(-t / 0.02)) * vel


def shaker(vel=1.0, open_=False):
    n = ns(0.16 if open_ else 0.07)
    t = tt(n)
    return filt(noise(n), "highpass", 6500, 1) * np.exp(-t / (0.06 if open_ else 0.022)) * vel * 0.5


def clap(vel=1.0):
    n = ns(0.3)
    sig = np.zeros(n)
    for off in (0.0, 0.012, 0.026):
        k = ns(off)
        b = band(noise(n - k), 900, 3800, 2) * np.exp(-tt(n - k) / 0.03)
        sig[k:] += b
    sig += band(noise(n), 900, 3500, 2) * np.exp(-tt(n) / 0.09) * 0.5
    return sig * vel * 0.6


def crash(dur=3.0, vel=1.0):
    n = ns(dur)
    t = tt(n)
    sig = filt(noise(n), "highpass", 4200, 2) * (0.8 * np.exp(-t / 0.8) + 0.2 * np.exp(-t / 2.0))
    sig += band(noise(n), 400, 1200, 1) * np.exp(-t / 0.4) * 0.15
    return sig * vel * 0.55


def riser(dur, vel=1.0):
    n = ns(dur)
    t = tt(n)
    sig = band(noise(n), 800, 7000, 1) * (t / dur) ** 2.2
    return sig * vel * 0.4


def bell(m, dur=3.0, vel=1.0):
    f = float(mtof(m))
    n = ns(dur)
    t = tt(n)
    sig = np.zeros(n)
    for ratio, amp, tau in ((1, 1, 1.2), (2.76, 0.6, 0.8), (5.4, 0.35, 0.5), (8.93, 0.2, 0.3), (13.3, 0.1, 0.2)):
        sig += amp * np.sin(PI2 * f * ratio * t) * np.exp(-t / (tau * dur / 3))
    return sig * 0.25 * vel


def whip(vel=1.0):
    n = ns(0.45)
    t = tt(n)
    crack = filt(noise(n), "highpass", 2200, 2) * np.exp(-t / 0.010)
    sweep = band(noise(n), 1200, 6500, 1) * np.exp(-t / 0.05) * 0.4
    swish = band(noise(n), 500, 4000, 1) * np.interp(t, [0, 0.06, 0.12, 0.2], [0, 0.4, 0.1, 0]) * 0.25
    return (crack + sweep + swish) * vel


# ----------------------------------------------------------------------------
# The theme
# ----------------------------------------------------------------------------
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4

CHORDS = {
    "Em": dict(bass=40, pcs={4, 7, 11}, pad=[52, 55, 59, 64], pow=52),
    "C": dict(bass=36, pcs={0, 4, 7}, pad=[48, 52, 55, 60], pow=48),
    "D": dict(bass=38, pcs={2, 6, 9}, pad=[50, 54, 57, 62], pow=50),
    "B7": dict(bass=35, pcs={11, 3, 6, 9}, pad=[47, 51, 54, 57], pow=47),
    "Am": dict(bass=33, pcs={9, 0, 4}, pad=[45, 52, 57, 60], pow=45),
}
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def n_(name):
    """'F#4' -> MIDI."""
    base = NOTE[name[0]]
    i = 1
    if name[i] in "#b":
        base += 1 if name[i] == "#" else -1
        i += 1
    return base + 12 * (int(name[i:]) + 1)


def harm_above(m, pcs):
    for d in (3, 4, 5):
        if (m + d) % 12 in pcs:
            return m + d
    return m + 4


def gallop_hits(bar_t, fn, offs=(0.0, 0.5, 0.75)):
    """Call fn(time, beat_index, hit_index) for the long-short-short gallop on every beat."""
    for b in range(4):
        for h, o in enumerate(offs):
            fn(bar_t + (b + o) * BEAT, b, h)


def guitar_gallop(mx, bar_t, chord, level=1.0, accent_first=True):
    root = CHORDS[chord]["pow"]
    tones = [root, root + 7, root + 12]

    def hit(t, b, h):
        v = (1.0 if h == 0 else 0.7) * level * (1.15 if (b == 0 and h == 0 and accent_first) else 1.0)
        for i, m in enumerate(tones):
            mx.add(pluck(m, 0.16 if h else 0.26, 0.6 * v, g=0.986, drive=1.4), t + i * 0.006, 0.33, pan=-0.35 + i * 0.05, send=0.12)

    gallop_hits(bar_t, hit)


def guitar_strum(mx, t, chord, down=True, vel=1.0, dur=1.4):
    pad = CHORDS[chord]["pad"]
    mids = [pad[0] - 12, pad[0], pad[1], pad[2], pad[3] if len(pad) > 3 else pad[0] + 12]
    order = mids if down else mids[::-1]
    for i, m in enumerate(order):
        mx.add(pluck(m, dur, 0.55 * vel, bright=0.6, g=0.9965), t + i * 0.012, 0.45, pan=0.35 - i * 0.06, send=0.18)


def bass_gallop(mx, bar_t, chord, level=1.0):
    root = CHORDS[chord]["bass"]

    def hit(t, b, h):
        m = root + (12 if (h == 2) else 0)
        mx.add(bass_note(m, 0.2 if h else 0.34, (1.0 if h == 0 else 0.8) * level), t, 0.50, pan=0.0)

    gallop_hits(bar_t, hit)


def drums_gallop(mx, bar_t, level=1.0, fill=False, crash_on=False):
    level = level * 0.5
    # kick: beats 1 and 3 plus a gallop pickup before 2 and 4
    for b, off in ((0, 0.0), (1, 0.75), (2, 0.0), (3, 0.75), (3, 0.5)):
        mx.add(kick(0.9 * level), bar_t + (b + off) * BEAT, 0.95)
    # snare backbeat + ghost notes
    for b in (1, 3):
        mx.add(snare(0.85 * level), bar_t + b * BEAT, 0.85, pan=0.05, send=0.1)
        mx.add(snare_ghost(0.45 * level), bar_t + (b - 0.25) * BEAT, 0.7, pan=0.05)
    # shaker on sixteenths
    for i in range(16):
        mx.add(shaker((0.9 if i % 4 == 0 else 0.5) * level, i % 4 == 2), bar_t + i * BEAT / 4, 0.55, pan=0.45 if i % 2 else 0.35)
    if crash_on:
        mx.add(crash(3.2), bar_t, 0.7, pan=-0.2, send=0.25)
    if fill:
        for i, m in enumerate((55, 52, 48, 45)):
            mx.add(tom(m, 0.9 * level), bar_t + (3 + i / 4) * BEAT, 0.8, pan=-0.4 + i * 0.25, send=0.12)


def snare_roll(mx, t0, dur, v0=0.15, v1=1.0, start_gap=0.09, end_gap=0.03):
    t = t0
    while t < t0 + dur:
        p = (t - t0) / dur
        mx.add(snare(v0 + (v1 - v0) * p), t, 0.45, pan=0.05, send=0.1)
        t += start_gap + (end_gap - start_gap) * p


def timp_roll(mx, t0, dur, m, v0=0.2, v1=1.0, gap=0.085):
    t = t0
    i = 0
    while t < t0 + dur:
        p = (t - t0) / dur
        mx.add(timp(m, 0.5, v0 + (v1 - v0) * p), t, 0.5, pan=-0.15 if i % 2 else 0.15, send=0.35)
        t += gap
        i += 1


MELODY_B = [  # (bar, chord, [(beat, dur, note)])
    ("C", [(0, 1.5, "G4"), (1.5, 0.5, "G4"), (2, 1, "C5"), (3, 1, "B4")]),
    ("D", [(0, 1.5, "A4"), (1.5, 0.5, "A4"), (2, 1, "D5"), (3, 1, "C5")]),
    ("Em", [(0, 2, "B4"), (2, 1, "E5"), (3, 0.5, "D5"), (3.5, 0.5, "B4")]),
    ("Em", [(0, 3, "E5"), (3, 1, "B4")]),
    ("C", [(0, 1.5, "G5"), (1.5, 0.5, "E5"), (2, 1, "G5"), (3, 1, "A5")]),
    ("D", [(0, 1.5, "F#5"), (1.5, 0.5, "D5"), (2, 1, "F#5"), (3, 1, "G5")]),
    ("B7", [(0, 1, "D#5"), (1, 1, "F#5"), (2, 1.5, "B5"), (3.5, 0.5, "A5")]),
    ("B7", [(0, 1, "A5"), (1, 1, "F#5"), (2, 2, "D#5")]),
]
LEAD_A = [
    ("Em", [(0, .5, "E4"), (.5, .5, "G4"), (1, 1, "B4"), (2, .5, "A4"), (2.5, .5, "G4"), (3, 1, "E4")]),
    ("Em", [(0, .5, "E4"), (.5, .5, "F4"), (1, 1, "G4"), (2, .5, "F4"), (2.5, .5, "E4"), (3, 1, "D#4")]),
    ("C", [(0, .5, "G4"), (.5, .5, "E4"), (1, 1, "C5"), (2, .5, "B4"), (2.5, .5, "A4"), (3, 1, "G4")]),
    ("B7", [(0, .5, "F#4"), (.5, .5, "A4"), (1, 1, "D#5"), (2, 2, "B4")]),
]


def play_melody(mx, bar_t, notes, chord, level=1.0, harmony=False, octave=0, send=0.3):
    for beat, dur, name in notes:
        m = n_(name) + octave
        t = bar_t + beat * BEAT
        d = dur * BEAT * 0.96
        mx.add(brass(m, d, level), t, 0.9, pan=-0.12, send=send)
        if harmony:
            mx.add(brass(harm_above(m, CHORDS[chord]["pcs"]), d, level * 0.8), t + 0.004, 0.8, pan=0.18, send=send)


def pad_chord(mx, bar_t, chord, bars=1, level=1.0, choir_=True):
    dur = BAR * bars
    for i, m in enumerate(CHORDS[chord]["pad"]):
        if choir_:
            mx.add(choir(m + 12 * (i == 0), dur, level), bar_t, 0.9, pan=-0.5 + i * 0.33, send=0.6)
        else:
            mx.add(pad_saw(m, dur, level), bar_t, 0.9, pan=-0.5 + i * 0.33, send=0.4)


def section_A(mx, t0, lead=True, level=1.0):
    seq = ["Em", "Em", "C", "D", "Em", "Em", "C", "B7"]
    for i, ch in enumerate(seq):
        bt = t0 + i * BAR
        guitar_gallop(mx, bt, ch, level)
        bass_gallop(mx, bt, ch, level)
        drums_gallop(mx, bt, level, fill=(i == 7), crash_on=(i == 0))
        if i in (2, 3, 6):  # brass answers
            hits = [(2.5, "B4"), (3, "E5"), (3.5, "G5")] if i != 6 else [(2.5, "G4"), (3, "B4"), (3.5, "D5")]
            for beat, name in hits:
                m = n_(name)
                mx.add(brass(m, 0.22, 0.9), bt + beat * BEAT, 0.85, pan=-0.1, send=0.3)
                mx.add(brass(m - 5, 0.22, 0.6), bt + beat * BEAT, 0.7, pan=0.15, send=0.3)
    if lead:
        for i, (ch, notes) in enumerate(LEAD_A):
            bt = t0 + (4 + i) * BAR
            for beat, dur, name in notes:
                mx.add(pluck(n_(name) + 12, dur * BEAT, 0.8, bright=0.7, g=0.9985), bt + beat * BEAT, 0.55, pan=0.3, send=0.25)
    # choir swell into the next section
    pad_chord(mx, t0 + 4 * BAR, "Em", 2, 0.5 * level)


def section_B(mx, t0, level=1.0, final=False):
    seq = [c for c, _ in MELODY_B]
    for i, (ch, notes) in enumerate(MELODY_B):
        bt = t0 + i * BAR
        guitar_gallop(mx, bt, ch, 0.9 * level) if not final else guitar_strum(mx, bt, ch, True, 1.0, BAR)
        if final:
            for b in (0.75, 1.5, 2.75, 3.5):
                guitar_strum(mx, bt + b * BEAT, ch, b in (1.5, 3.5), 0.8, BEAT)
        bass_gallop(mx, bt, ch, level)
        drums_gallop(mx, bt, level, fill=(i in (3, 7)), crash_on=(i == 0 or (final and i == 4)))
        pad_chord(mx, bt, ch, 1, 0.9 * level, choir_=True)
        play_melody(mx, bt, notes, ch, level, harmony=final, octave=0)
        if final:
            for beat, dur, name in notes:  # low brass doubling an octave down
                mx.add(brass(n_(name) - 12, dur * BEAT * 0.95, 0.7), bt + beat * BEAT, 0.8, pan=0.05, send=0.3)
        if i % 2 == 0:
            mx.add(timp(CHORDS[ch]["bass"] + 12, 1.2, 0.8), bt, 0.5, send=0.3)


def section_C(mx, t0, level=1.0):
    """Breakdown: choir + pulsing low strings, building snare roll."""
    seq = ["Am", "Am", "B7", "B7"]
    for i, ch in enumerate(seq):
        bt = t0 + i * BAR
        pad_chord(mx, bt, ch, 1, 1.0, choir_=True)
        mx.add(bass_note(CHORDS[ch]["bass"], BAR * 0.95, 0.9), bt, 0.9)
        for b in range(4):  # heartbeat pulses
            mx.add(kick(0.55 + 0.1 * i), bt + b * BEAT, 0.5)
        for k, m in enumerate((n_("E5"), n_("D5"), n_("C5"), n_("B4")) if i < 2 else (n_("F#5"), n_("D#5"), n_("B4"), n_("F#4"))):
            mx.add(bell(m, 2.0, 0.9), bt + k * BEAT, 0.6, pan=-0.3 + 0.2 * k, send=0.5)
    snare_roll(mx, t0 + 2 * BAR, 2 * BAR, 0.1, 1.0)
    timp_roll(mx, t0 + 3 * BAR, BAR, 35 + 12, 0.3, 1.0)
    mx.add(riser(4 * BAR, 0.9), t0, 0.7, pan=0.0, send=0.3)


def intro(mx, t0):
    # bars 0-1: low drone + timpani heartbeat; bars 2-3: roll, riser, fanfare lead-in
    for m in (28, 40, 47):
        mx.add(pad_saw(m, 2 * BAR + 0.5, 1.0, att=1.5, rel=0.8, cutoff=500), t0, 0.9, pan=0.0, send=0.5)
    for b in range(8):
        mx.add(timp(40, 1.0, 0.45 + 0.05 * b), t0 + b * BEAT, 0.6, send=0.4)
    mx.add(bell(n_("E5"), 4.0, 1.0), t0 + 2 * BAR - 0.02, 0.7, pan=-0.2, send=0.7)
    mx.add(bell(n_("B5"), 4.0, 0.8), t0 + 2 * BAR + BEAT, 0.6, pan=0.25, send=0.7)
    for m in (40, 47, 52, 55):
        mx.add(choir(m + 12, 2 * BAR, 0.55, att=1.2), t0 + 2 * BAR, 0.9, pan=(m % 5 - 2) * 0.2, send=0.6)
    timp_roll(mx, t0 + 2 * BAR, 2 * BAR - 0.05, 40, 0.15, 1.0)
    snare_roll(mx, t0 + 3 * BAR - 0.05, BAR, 0.1, 1.0, 0.1, 0.028)
    mx.add(riser(2 * BAR, 0.9), t0 + 2 * BAR, 0.8, send=0.3)
    # fanfare triplet pickup on the last beat
    for k, name in enumerate(("B4", "E5", "G5")):
        mx.add(brass(n_(name), 0.17, 1.0), t0 + 4 * BAR - BEAT + k * BEAT / 3, 0.9, send=0.3)


def finale_hit(mx, t, level=1.0):
    for m in (n_("E3"), n_("B3"), n_("E4"), n_("G4"), n_("B4"), n_("E5"), n_("G5")):
        mx.add(brass(m, BEAT * 3, level), t, 0.55, pan=(m % 7 - 3) * 0.12, send=0.35)
    mx.add(crash(4.0), t, 0.9, send=0.4)
    mx.add(timp(40, 2.0, 1.0), t, 1.0, send=0.4)
    mx.add(kick(1.0), t, 1.0)
    mx.add(snare(1.0), t, 0.9, send=0.2)


def hit_in(mx, t):
    """The 'pose' fanfare hit that opens section A."""
    for m in (n_("E3"), n_("B3"), n_("E4"), n_("G4"), n_("B4"), n_("E5")):
        mx.add(brass(m, BEAT * 1.6, 1.0), t, 0.55, pan=(m % 7 - 3) * 0.1, send=0.35)
    mx.add(timp(40, 1.6, 1.0), t, 1.0, send=0.4)


def finalize_music(mx, length_s, wet=1.0, rt60=2.4, loop=True, gain=0.9):
    out = mx.render(rt60, wet)
    n = ns(length_s)
    if loop:
        out = loop_wrap(out, n)
    else:
        out = out[:n]
    out = softclip(out * 0.9, 1.15)
    return normalise(out, gain)


def build_music():
    pieces = {}
    # --- race theme (loop): A B C Final, 28 bars -------------------------------
    L = 28 * BAR
    mx = Mix(L + 6)
    section_A(mx, 0, lead=True, level=0.95)
    section_B(mx, 8 * BAR, level=1.0)
    section_C(mx, 16 * BAR, level=1.0)
    section_B(mx, 20 * BAR, level=1.05, final=True)
    pieces["theme_race"] = finalize_music(mx, L)

    # --- title theme (loops): intro (4) + A (8) + B (8) = 20 bars ---------------
    L2 = 20 * BAR
    mx = Mix(L2 + 6)
    intro(mx, 0)
    hit_in(mx, 4 * BAR)
    section_A(mx, 4 * BAR, lead=True, level=1.0)
    section_B(mx, 12 * BAR, level=1.0)
    pieces["theme_title"] = finalize_music(mx, L2)

    # --- start stinger: 'pose' hit -------------------------------------------------
    mx = Mix(7)
    for k, name in enumerate(("B4", "E5", "G5")):
        mx.add(brass(n_(name), 0.15, 1.0), k * BEAT / 3, 0.9, send=0.3)
    finale_hit(mx, BEAT, 1.0)
    pieces["stinger_start"] = finalize_music(mx, 6.0, loop=False)
    return pieces


# ----------------------------------------------------------------------------
# Sound effects
# ----------------------------------------------------------------------------
def hoof(seed, size=1.0):
    r = np.random.default_rng(seed)
    n = ns(0.28)
    t = tt(n)
    f = 58 + 22 * r.random()
    thump = np.sin(PI2 * np.cumsum(f * (1 + 0.7 * np.exp(-t / 0.03))) / SR) * np.exp(-t / 0.07) * 1.1
    body = band(r.uniform(-1, 1, n), 180 + 120 * r.random(), 900 + 500 * r.random(), 2) * np.exp(-t / 0.045)
    # gritty dirt: noise gated into small grains
    grains = (r.random(n) > 0.8).astype(float)
    grit = filt(r.uniform(-1, 1, n) * grains, "highpass", 1800, 1) * np.exp(-t / 0.06) * 0.8
    click = filt(r.uniform(-1, 1, n), "highpass", 2500, 1) * np.exp(-t / 0.004) * 0.35
    return (thump * 0.9 + body * 0.9 + grit * 0.35 + click * 0.5) * size


def hoof_pair(seed):
    a = hoof(seed)
    b = hoof(seed + 50, 0.7)
    out = np.zeros(ns(0.4))
    out[: len(a)] += a
    k = ns(0.045)
    out[k : k + len(b)] += b
    return out


def whinny(seed=1, pitch=1.0, dur=1.7):
    r = np.random.default_rng(seed)
    n = ns(dur)
    t = tt(n)
    # pitch contour: quick rise, wobbling squeal, long falling "whuuoh"
    c = np.interp(t, [0, 0.06, 0.28, 0.55, 0.9, dur * 0.8, dur], [420, 760, 1280, 1180, 920, 560, 380]) * pitch
    c = c * (1 + 0.045 * np.sin(PI2 * 7.5 * t) * np.clip(t / 0.5, 0, 1)) * (1 + 0.012 * r.normal(size=n).cumsum() / np.sqrt(n) * 4)
    ph = np.cumsum(c) / SR
    H = 36
    sig = np.zeros(n)
    f1 = np.interp(t, [0, 0.3, dur], [900, 1250, 700])
    f2 = np.interp(t, [0, 0.3, dur], [1900, 2500, 1600])
    for k in range(1, H + 1):
        hf = k * c
        w = np.exp(-((hf - f1) / 420) ** 2) + 0.7 * np.exp(-((hf - f2) / 650) ** 2) + 0.12 / k
        sig += w / (k ** 0.35) * np.sin(PI2 * k * ph)
    # throaty amplitude rattle
    rattle = 0.78 + 0.22 * np.sin(PI2 * 34 * t + 3 * np.sin(PI2 * 5 * t))
    breath = band(r.uniform(-1, 1, n), 1500, 6000, 1) * 0.22
    env = np.interp(t, [0, 0.04, 0.25, 0.9, dur * 0.85, dur], [0, 0.85, 1, 0.8, 0.35, 0])
    out = (sig * 0.09 * rattle + breath * 0.5 * np.clip(env * 1.3, 0, 1)) * env
    return out


def nicker(seed=2, dur=0.9):
    r = np.random.default_rng(seed)
    n = ns(dur)
    t = tt(n)
    c = np.interp(t, [0, 0.2, dur], [190, 240, 150])
    ph = np.cumsum(c) / SR
    amp = 0.5 + 0.5 * np.sin(PI2 * 22 * t)
    sig = np.zeros(n)
    for k in range(1, 22):
        hf = k * c
        w = np.exp(-((hf - 600) / 350) ** 2) + 0.4 * np.exp(-((hf - 1400) / 600) ** 2) + 0.1 / k
        sig += w / k ** 0.5 * np.sin(PI2 * k * ph)
    breath = band(r.uniform(-1, 1, n), 400, 2500, 1) * 0.12
    env = np.interp(t, [0, 0.08, 0.6, dur], [0, 1, 0.6, 0])
    return (sig * 0.10 * (0.55 + 0.45 * amp) + breath) * env


def snort(seed=3, dur=0.55):
    r = np.random.default_rng(seed)
    n = ns(dur)
    t = tt(n)
    nz = r.uniform(-1, 1, n)
    bp = filt(nz, "highpass", 500, 1)
    bp = filt(bp, "lowpass", 3500, 1)
    wet = 0.6 + 0.4 * np.sin(PI2 * 38 * t)
    env = np.interp(t, [0, 0.02, 0.15, dur], [0, 1, 0.55, 0])
    thump = np.sin(PI2 * 110 * t) * np.exp(-t / 0.05) * 0.4
    return (bp * wet * 0.7 + thump) * env


def breath(seed=4, dur=0.9, vel=0.5):
    r = np.random.default_rng(seed)
    n = ns(dur)
    t = tt(n)
    nz = band(r.uniform(-1, 1, n), 300, 2400, 1)
    env = np.interp(t, [0, 0.28, dur], [0, 1, 0]) ** 1.5
    return nz * env * vel


def creak(seed=5, dur=0.42):
    r = np.random.default_rng(seed)
    n = ns(dur)
    t = tt(n)
    f = np.interp(t, [0, dur * 0.4, dur], [320, 560, 280])
    ph = np.cumsum(f * (1 + 0.15 * r.normal(size=n).cumsum() / np.sqrt(n) * 2)) / SR
    saw = 2 * (ph % 1) - 1
    sig = band(saw, 300, 1800, 1) * (0.5 + 0.5 * np.sign(np.sin(PI2 * 46 * t + 1)) * 0.5)
    env = np.interp(t, [0, 0.05, dur * 0.7, dur], [0, 1, 0.6, 0])
    return sig * env * 0.18


def jingle(seed=6, dur=0.5, hits=6):
    r = np.random.default_rng(seed)
    n = ns(dur)
    out = np.zeros(n)
    for _ in range(hits):
        t0 = ns(r.random() * dur * 0.55)
        f = 3200 + r.random() * 4200
        m = n - t0
        t = tt(m)
        p = np.sin(PI2 * f * t) + 0.5 * np.sin(PI2 * f * 2.31 * t)
        out[t0:] += p * np.exp(-t / (0.03 + 0.05 * r.random())) * (0.3 + 0.7 * r.random())
    return out * 0.18


def whoosh(dur=0.5, up=True, vel=0.8):
    n = ns(dur)
    t = tt(n)
    nz = noise(n)
    out = np.zeros(n)
    B = 1024
    for i in range(0, n, B):
        p = i / n
        fc = (500 + 3500 * p) if up else (4000 - 3300 * p)
        seg = nz[i : i + B]
        out[i : i + len(seg)] = band(np.pad(seg, (B, 0)), fc * 0.6, fc * 1.4, 1)[B : B + len(seg)]
    env = np.interp(t, [0, dur * 0.45, dur], [0, 1, 0]) if up else np.interp(t, [0, dur * 0.1, dur], [0, 1, 0])
    return out * env * vel * 1.2


def skid(dur=0.9):
    n = ns(dur)
    t = tt(n)
    nz = filt(noise(n), "lowpass", 3000, 1)
    grit = band(noise(n), 600, 2500, 1)
    env = np.interp(t, [0, 0.05, dur * 0.6, dur], [0, 1, 0.6, 0])
    wob = 0.75 + 0.25 * np.sin(PI2 * 17 * t)
    return (nz * 0.3 + grit * 0.6 * wob) * env * 0.6


def land(dur=0.5):
    n = ns(dur)
    t = tt(n)
    th = np.sin(PI2 * np.cumsum(70 * (1 + 0.8 * np.exp(-t / 0.04))) / SR) * np.exp(-t / 0.12)
    dust = band(noise(n), 200, 1800, 2) * np.exp(-t / 0.12) * 0.7
    clip = filt(noise(n), "highpass", 2500, 1) * np.exp(-t / 0.006) * 0.3
    return th * 0.9 + dust + clip


def pant(dur=0.8):
    out = np.zeros(ns(dur))
    for i, off in enumerate((0.0, 0.34)):
        b = breath(20 + i, 0.4, 0.8)
        k = ns(off)
        out[k : k + len(b)] += b
    return out


def thunder_gallop(dur=0.9):
    n = ns(dur)
    t = tt(n)
    out = np.zeros(n)
    for i in range(7):
        k = ns(i * 0.115)
        h = hoof(70 + i, 1.0 - i * 0.05)
        out[k : k + len(h)] += h[: n - k] * (0.5 + 0.1 * (i % 2))
    out += filt(noise(n), "lowpass", 400, 2) * np.interp(t, [0, 0.3, dur], [0, 0.35, 0])
    return out


def ui_click():
    n = ns(0.12)
    t = tt(n)
    return (np.sin(PI2 * 880 * t) * np.exp(-t / 0.012) + 0.6 * np.sin(PI2 * 1320 * t) * np.exp(-t / 0.02) + filt(noise(n), "highpass", 3000, 1) * np.exp(-t / 0.004) * 0.3) * 0.5


def ui_hover():
    n = ns(0.08)
    t = tt(n)
    return np.sin(PI2 * 1500 * t) * np.exp(-t / 0.012) * 0.25


def gogogo(dur=8.0):
    """Ominous low drone with pulsing menace, loops seamlessly."""
    n = ns(dur)
    t = tt(n)
    f = 41.2
    sub = np.sin(PI2 * f * t) + 0.5 * np.sin(PI2 * 2 * f * t) + 0.25 * np.sin(PI2 * 3 * f * t)
    pulse = 0.55 + 0.45 * np.sin(PI2 * (1 / (dur / 16)) * t - 1.2)
    nz = filt(noise(n), "lowpass", 500, 2) * (0.5 + 0.5 * np.sin(PI2 * 2 * t))
    cl = np.zeros(n)
    for fr in (f * 6, f * 6.05, f * 9.02):
        cl += np.sin(PI2 * fr * t) * 0.07
    out = sub * 0.4 * pulse + nz * 0.5 + cl * (0.5 + 0.5 * np.sin(PI2 * t / dur * 3))
    # crossfade ends for a seamless loop
    xf = ns(0.5)
    head, tail = out[:xf].copy(), out[-xf:].copy()
    w = np.linspace(0, 1, xf)
    out[:xf] = head * w + tail * (1 - w)
    return out[:-xf]


def wind_loop(dur=12.0):
    n = ns(dur)
    t = tt(n)
    nz = noise(n)
    low = filt(nz, "lowpass", 600, 2)
    mid = band(nz, 500, 2200, 2)
    gust = 0.55 + 0.45 * np.sin(PI2 * t / dur * 2 + 1) * np.sin(PI2 * t / dur * 3 + 0.5)
    out = low * 0.5 * gust + mid * 0.22 * (0.4 + gust)
    xf = ns(1.0)
    w = np.linspace(0, 1, xf)
    head, tail = out[:xf].copy(), out[-xf:].copy()
    out[:xf] = head * w + tail * (1 - w)
    return out[:-xf]


def fire_loop(dur=8.0):
    n = ns(dur)
    t = tt(n)
    base = filt(noise(n), "lowpass", 900, 2) * 0.12
    crackles = np.zeros(n)
    for _ in range(int(dur * 22)):
        k = int(rng.random() * (n - 2000))
        L = int(300 + rng.random() * 1200)
        pop = band(noise(L), 1500 + rng.random() * 3000, 6000, 1) * np.exp(-tt(L) / (0.002 + 0.006 * rng.random()))
        crackles[k : k + L] += pop * (0.2 + 0.8 * rng.random())
    out = base + crackles * 0.5
    xf = ns(0.5)
    w = np.linspace(0, 1, xf)
    head, tail = out[:xf].copy(), out[-xf:].copy()
    out[:xf] = head * w + tail * (1 - w)
    return out[:-xf]


def vulture():
    n = ns(1.3)
    t = tt(n)
    c = np.interp(t, [0, 0.15, 0.5, 1.3], [1900, 2500, 1700, 1200])
    ph = np.cumsum(c * (1 + 0.04 * np.sin(PI2 * 9 * t))) / SR
    sig = np.sin(PI2 * ph) + 0.4 * np.sin(PI2 * 2 * ph)
    return band(sig + 0.2 * noise(n), 900, 4500, 1) * np.interp(t, [0, 0.05, 0.5, 1.3], [0, 1, 0.7, 0]) * 0.25


def stamina_ready():
    n = ns(0.5)
    t = tt(n)
    return (np.sin(PI2 * 660 * t) * np.exp(-t / 0.08) + np.sin(PI2 * 990 * t) * np.exp(-t / 0.12) * np.interp(t, [0, 0.08, 0.1, 0.5], [0, 0, 1, 0])) * 0.4


def build_sfx():
    s = {}
    for i in range(1, 5):
        s[f"hoof_dirt_{i}"] = hoof_pair(i * 13)[: ns(0.32)]
    for i in range(1, 5):
        s[f"hoof_soft_{i}"] = hoof(i * 31 + 5, 0.75)
    s["gallop_burst"] = thunder_gallop()
    s["whinny_1"] = whinny(1, 1.0, 1.7)
    s["whinny_2"] = whinny(7, 0.9, 1.45)
    s["whinny_3"] = whinny(9, 1.1, 1.2)
    s["nicker"] = nicker(2)
    s["snort_1"] = snort(3)
    s["snort_2"] = snort(8, 0.45)
    s["breath_1"] = breath(4, 0.9, 0.55)
    s["breath_2"] = breath(14, 1.1, 0.5)
    s["creak_1"] = creak(5)
    s["creak_2"] = creak(15, 0.5)
    s["jingle_1"] = jingle(6)
    s["jingle_2"] = jingle(16, 0.6, 8)
    s["whip_crack"] = whip()
    s["skid"] = skid()
    s["land"] = land()
    s["jump"] = whoosh(0.35, True, 0.7)
    s["whoosh_boost"] = whoosh(0.8, True, 0.9)
    s["pant"] = pant()
    s["stamina_ready"] = stamina_ready()
    s["ui_click"] = ui_click()
    s["ui_hover"] = ui_hover()
    s["vulture"] = vulture()
    s["ambience_gogogo"] = gogogo()
    s["ambience_wind"] = wind_loop()
    s["ambience_fire"] = fire_loop()
    return s


# meta used by the Luau side (volume 0-1, loop, positional = 3D emitter)
META = {
    "theme_title": dict(kind="music", loop=True, volume=0.55),
    "theme_race": dict(kind="music", loop=True, volume=0.42),
    "stinger_start": dict(kind="music", loop=False, volume=0.8),
    "ambience_gogogo": dict(kind="ambience", loop=True, volume=0.35),
    "ambience_wind": dict(kind="ambience", loop=True, volume=0.28),
    "ambience_fire": dict(kind="ambience", loop=True, volume=0.55, positional=True),
}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    manifest = {}
    if which in ("all", "music"):
        for name, x in build_music().items():
            write_ogg(name, x)
            manifest[name] = dict(META[name], seconds=round(len(x) / SR, 2), file=name + ".ogg")
            print(f"music {name}: {len(x) / SR:.1f}s peak {np.max(np.abs(x)):.2f} rms {np.sqrt(np.mean(x ** 2)):.3f}")
    if which in ("all", "sfx"):
        for name, x in build_sfx().items():
            x = np.nan_to_num(x)
            peak = 0.8 if not name.startswith("ambience") else 0.7
            x = normalise(x, peak)
            if name in ("hoof_soft_1", "hoof_soft_2", "hoof_soft_3", "hoof_soft_4"):
                x *= 0.85
            fade = ns(0.004)
            if not META.get(name, {}).get("loop"):
                x[:fade] *= np.linspace(0, 1, fade)
                x[-ns(0.01) :] *= np.linspace(1, 0, ns(0.01))
            write_ogg(name, x)
            meta = dict(kind="sfx", loop=False, volume=0.8)
            meta.update(META.get(name, {}))
            manifest[name] = dict(meta, seconds=round(len(x) / SR, 2), file=name + ".ogg")
        print(f"sfx: {len([k for k in manifest if manifest[k]['kind'] != 'music'])} files")
    old = {}
    mp = os.path.join(OUT, "manifest.json")
    if os.path.exists(mp):
        old = json.load(open(mp))
    old.update(manifest)
    with open(mp, "w") as f:
        json.dump(old, f, indent=2, sort_keys=True)
    print("manifest ->", mp)


if __name__ == "__main__":
    main()
