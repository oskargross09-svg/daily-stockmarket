"""Musikbett (News-Bed, 96 BPM, a-Moll) und Soundeffekte synthetisieren und mit der Stimme mischen.
Regeln: Designsystem, motion.md › „Ton: Musik & Soundeffekte“."""
import subprocess, wave
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def hz(m): return 440 * 2 ** ((m - 69) / 12)

def add(buf, x, t, g=1.0):
    s = int(t * SR); e = min(len(buf), s + len(x))
    if 0 <= s < len(buf) and e > s: buf[s:e] += x[:e - s] * g

def music_bed(T, N, rng):
    BPM = 96; beat = 60 / BPM; bar = 4 * beat
    CH = [[57, 60, 64], [53, 57, 60], [48, 55, 60], [55, 59, 62]]; ROOT = [45, 41, 36, 43]
    pad = np.zeros(N); bass = np.zeros(N); drums = np.zeros(N); pl = np.zeros(N)
    for b in range(int(T / bar) + 2):
        t0 = b * bar; c = CH[b % 4]
        n = int(bar * SR * 1.05); t = np.arange(n) / SR; v = np.zeros(n)
        for m in c + [c[0] + 12]:
            for det in (-0.08, 0.08):
                v += 2 * ((t * hz(m) * 2 ** (det / 12)) % 1) - 1
        add(pad, v * np.minimum(1, t / 0.6) * np.minimum(1, (bar * 1.05 - t) / 0.5), t0)
        for bt, ln in [(0, 1.6), (2, 1.2), (3.5, 0.45)]:
            n = int(ln * beat * SR); t = np.arange(n) / SR; f = hz(ROOT[b % 4])
            x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
            e = np.minimum(1, t / 0.01) * (0.5 + 0.5 * np.exp(-t / 0.35)) * np.minimum(1, (n / SR - t) / 0.05)
            add(bass, x * e, t0 + bt * beat)
        for bt in (0, 2):
            n = int(0.35 * SR); t = np.arange(n) / SR; f = 48 + 70 * np.exp(-t / 0.03)
            add(drums, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12), t0 + bt * beat, 0.9)
        for bt in (1, 3):
            n = int(0.12 * SR); add(drums, bp(rng.standard_normal(n), 900, 3000) * np.exp(-np.arange(n) / SR / 0.03), t0 + bt * beat, 0.35)
        for k in range(8):
            n = int(0.05 * SR); add(drums, hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR / 0.012), t0 + k * beat / 2, 0.18 if k % 2 else 0.1)
        arp = [c[0] + 12, c[1] + 12, c[2] + 12, c[1] + 12, c[0] + 24, c[2] + 12, c[1] + 12, c[2] + 12]
        for k, m in enumerate(arp):
            n = int(0.4 * SR); t = np.arange(n) / SR; f = hz(m)
            add(pl, (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)) * np.exp(-t / 0.12), t0 + k * beat / 2)
    m = lp(pad, 1400) / 8 * 0.22 + lp(bass, 400) * 0.30 + drums * 0.28 + lp(pl, 3500) * 0.10
    f = np.ones(N); i0 = int((T - 1.6) * SR); i1 = int(T * SR)
    f[i0:i1] = np.linspace(1, 0, i1 - i0) ** 1.5; f[i1:] = 0
    m *= f; m[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    return m

def make_sfx(tl, N, rng):
    sfx = np.zeros(N)
    def whoosh(dur=0.8, lo=300, hi=4000, g=1.0):
        n = int(dur * SR); t = np.arange(n) / SR; x = rng.standard_normal(n)
        a = bp(x, lo * 0.7, lo * 2.0); b = bp(x, hi * 0.5, min(hi * 1.5, SR / 2 - 100))
        p = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
        return (a / (np.abs(a).max() + 1e-9) * (1 - p) * 0.6 + b / (np.abs(b).max() + 1e-9) * p) * p * g
    def click(f=1800, d=0.035, g=1.0):
        n = int(0.08 * SR); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * f * t) * np.exp(-t / d) + 0.4 * hp(rng.standard_normal(n), 3000) * np.exp(-t / 0.006)) * g
    def pop(g=1.0):
        n = int(0.18 * SR); t = np.arange(n) / SR; f = 520 + 380 * np.exp(-t / 0.02)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * g
    def ticks(t0, dur=0.9, g=1.0):
        for i in range(14):
            add(sfx, click(2600 + 200 * (i % 2), 0.012, 0.25 * g), t0 + dur * (1 - (1 - i / 14) ** 0.5))
    def chime(t0, notes=(81, 88), g=1.0):
        for j, m in enumerate(notes):
            n = int(1.6 * SR); t = np.arange(n) / SR; f = hz(m)
            add(sfx, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t / 0.15)) * np.exp(-t / 0.6) * g, t0 + j * 0.11)
    def impact(t0, g=1.0):
        n = int(1.2 * SR); t = np.arange(n) / SR; f = 40 + 90 * np.exp(-t / 0.05)
        add(sfx, (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35) + 0.3 * lp(rng.standard_normal(n), 900) * np.exp(-t / 0.08)) * g, t0)

    impact(0.02, 0.55); chime(0.1, (76, 83), 0.18)
    for i, sc in enumerate(tl["scenes"]):
        if i > 0:
            add(sfx, whoosh(0.8, 800, 6000, 0.35) if sc.get("transition") == "line" else whoosh(0.8, 250, 3500, 0.55), sc["swap"] - 0.4)
        if sc["type"] == "outro":
            chime(sc["swap"] + 0.05, (81, 88), 0.22)
            add(sfx, pop(0.22), sc["nextAt"]); add(sfx, pop(0.22), sc["subAt"]); chime(sc["subAt"] + 0.05, (88, 93), 0.12)
            continue
        add(sfx, pop(0.22), sc["headerAt"]); add(sfx, click(1500, 0.03, 0.18), sc["headerAt"] + 0.08)
        for o in sc.get("objects", []):
            if o.get("slideIn"): add(sfx, whoosh(0.35, 1500, 5000, 0.2), o["appear"] - 0.24)
            add(sfx, pop(0.27), o["appear"])
            if o["kind"] in ("quote", "kennzahl"): ticks(o["countAt"])
            if o["kind"] == "bars":
                for j in range(len(o["rows"])): add(sfx, click(900 + 150 * j, 0.04, 0.2), o["countAt"] + j * 0.08)
    return sfx

def make_mix(tl, voice_path, out_path):
    T = tl["total"]; N = int(T * SR) + SR; rng = np.random.default_rng(7)
    tmp = voice_path.replace(".wav", "48.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", voice_path, "-ar", str(SR), "-ac", "1", tmp], check=True)
    with wave.open(tmp) as w:
        voice = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    v = np.zeros(N); v[:min(N, len(voice))] = voice[:N]; v = hp(v, 80)
    blk = 480; gb = []; cur = 0.0
    for i in range(0, N, blk):
        tgt = 1.0 if np.sqrt(np.mean(v[i:i + blk] ** 2)) > 0.01 else 0.0
        cur += (tgt - cur) * (1 - np.exp(-blk / ((0.08 if tgt > cur else 0.45) * SR))); gb.append(cur)
    duck = 10 ** (-9 * np.repeat(gb, blk)[:N] / 20)
    norm = lambda x, p: x / (np.abs(x).max() + 1e-9) * p
    mix = norm(v, 0.85) + norm(music_bed(T, N, rng), 0.16) * duck + norm(make_sfx(tl, N, rng), 0.30)
    mix = np.tanh(mix[:int(T * SR)] * 1.1) / np.tanh(1.1)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
