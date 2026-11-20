"""Story-JSON -> fertiges Daily-Stockmarket-Short (MP4, 1080x1920, 30 fps).

Aufruf:
    python3 pipeline/make_video.py stories/2026-11-20_18.json            # komplettes Video
    python3 pipeline/make_video.py stories/2026-11-20_18.json --stills   # nur Kontrollbilder (sheet.jpg)

Ergebnis: build/<name>/<name>.mp4, build/<name>/sheet.jpg, build/<name>/timeline.json
"""
import asyncio, datetime as dt, json, os, re, shutil, subprocess, sys, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = f"{ROOT}/pipeline/template"
MODELS = os.environ.get("DS_MODELS", os.path.expanduser("~/.cache/daily-stockmarket"))
VOICE = f"{MODELS}/de-thorsten-low.onnx"
FPS = 30
GAP, SCENE_GAP, LEAD, TAIL = 0.30, 0.85, 0.45, 1.4
WOCHENTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
NEXT = {"06": ("12:00", "zwölf"), "12": ("18:00", "achtzehn"), "18": ("24:00", "Mitternacht"), "24": ("06:00", "sechs")}

def log(*a): print(*a, flush=True)

# ---------------------------------------------------------------- Prüfung
def validate(st):
    errs, warns = [], []
    for k in ("date", "edition", "mood", "ticker", "scenes", "title", "description"):
        if k not in st: errs.append(f"Feld fehlt: {k}")
    if st.get("edition") not in NEXT: errs.append("edition muss 06, 12, 18 oder 24 sein")
    if st.get("mood") not in ("up", "down", "flat", "politik"): errs.append("mood: up | down | flat | politik")
    words = 0
    for i, sc in enumerate(st.get("scenes", [])):
        t = sc.get("type")
        if t not in ("hook", "news", "fazit"): errs.append(f"Szene {i}: type hook | news | fazit")
        if sc.get("dir") not in ("up", "down", "flat", "politik"): errs.append(f"Szene {i}: dir fehlt/falsch")
        h = sc.get("headline", "")
        if len(h.replace("*", "")) > 52: warns.append(f"Szene {i}: Headline zu lang ({len(h)} Zeichen, max. ~52)")
        if "!" in h or "?" in h: errs.append(f"Szene {i}: keine ! oder ? in Headlines")
        if not sc.get("source"): errs.append(f"Szene {i}: source fehlt")
        if not sc.get("lines"): errs.append(f"Szene {i}: lines fehlt")
        for l in sc.get("lines", []):
            words += len(l["cap"].split())
            if "ß" in l["cap"]: errs.append(f"Szene {i}: ß statt ss: {l['cap'][:40]}")
        if not sc.get("objects"): errs.append(f"Szene {i}: mindestens ein Objekt")
        for o in sc.get("objects", []):
            if o.get("at", 0) >= len(sc.get("lines", [])): errs.append(f"Szene {i}: Objekt at={o.get('at')} > Anzahl Sätze")
            if o.get("kind") == "kennzahl" and len(f"{o.get('value')}{o.get('unit','')}") > 10:
                warns.append(f"Szene {i}: Kennzahl evtl. zu breit")
    if not (85 <= words <= 140): warns.append(f"Sprechtext {words} Wörter (Ziel 95–130 → 45–60 s)")
    return errs, warns

# ---------------------------------------------------------------- Stimme
def synth(text, path):
    subprocess.run([sys.executable, "-m", "piper", "-m", VOICE, "-f", path, "--length-scale", "0.92",
                    "--sentence-silence", "0.12"], input=text.encode(), check=True, stderr=subprocess.DEVNULL)
    with wave.open(path) as w:
        sr = w.getframerate(); d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    idx = np.where(np.abs(d.astype(np.float32)) > 300)[0]
    return sr, d[max(0, idx[0] - int(.02 * sr)): idx[-1] + int(.06 * sr)]

def build_timeline(st, out):
    ed = st["edition"]; nxt = NEXT[ed]
    scenes = [dict(sc) for sc in st["scenes"]]
    scenes.append({"type": "outro", "next": nxt[0], "lines": [
        {"cap": f"Das nächste Update gibt es um {nxt[0][:2].lstrip('0') if nxt[0] != '24:00' else 'Mitternacht'}{' Uhr' if nxt[0] != '24:00' else ''}.",
         "tts": f"Das nächste Update gibt es um {nxt[1]}{'' if nxt[1] == 'Mitternacht' else ' Uhr'}."},
        {"cap": "Abonnieren und 4× täglich informiert bleiben.", "tts": "Abonnieren, und viermal täglich informiert bleiben."}]})
    say = st.get("say", {})
    lines, t, sr, clips = [], LEAD, None, []
    for si, sc in enumerate(scenes):
        sc["lineIdx"] = []
        for li, l in enumerate(sc["lines"]):
            if lines: t += GAP if li else SCENE_GAP
            txt = l.get("tts") or l["cap"]
            for a, b in say.items(): txt = re.sub(rf"\b{re.escape(a)}\b", b, txt)
            sr, d = synth(txt, f"{out}/l{len(lines):02d}.wav")
            dur = len(d) / sr
            lines.append({"scene": si, "cap": l["cap"], "start": round(t, 3), "end": round(t + dur, 3)})
            clips.append((t, d)); sc["lineIdx"].append(len(lines) - 1); t += dur
    total = t + TAIL
    mix = np.zeros(int(total * sr) + 1, dtype=np.float32)
    for s, d in clips:
        i = int(s * sr); mix[i:i + len(d)] += d.astype(np.float32)
    mix = mix / np.abs(mix).max() * 0.89 * 32767
    with wave.open(f"{out}/voice.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(mix.astype(np.int16).tobytes())
    n = int(total * FPS) + 1; hop = sr / FPS
    rms = np.array([np.sqrt(np.mean(mix[int(k * hop):int((k + 1) * hop)] ** 2) + 1e-9) for k in range(n)]); rms /= rms.max()
    sm = np.zeros_like(rms); v = 0
    for k, r in enumerate(rms): v += (r - v) * (0.6 if r > v else 0.25); sm[k] = v

    # Szenen-Ereignisse
    mood = st["mood"]
    for si, sc in enumerate(scenes):
        ls = lambda i: lines[sc["lineIdx"][i]]["start"]
        sc["start"] = lines[sc["lineIdx"][0]]["start"]; sc["end"] = lines[sc["lineIdx"][-1]]["end"]
        sc["swap"] = 0 if si == 0 else round((scenes[si - 1]["end"] + sc["start"]) / 2, 3)
        sc["headerAt"] = 0.1 if si == 0 else sc["swap"] + 0.05
        sc["transition"] = "line" if sc["type"] == "fazit" else "wipe"
        typ = sc["type"]; d = sc.get("dir", "flat")
        sc["layout"] = {"hook": "mod", "fazit": "mod", "news": "data", "outro": "outro"}[typ]
        if typ in ("hook", "fazit"):
            sc["pose"] = {"down": {"arm": "kinn" if typ == "hook" else None, "brauen": "besorgt", "rest": "besorgt"},
                          "up": {"arm": "erklaeren", "brauen": "froh", "rest": "laecheln"}}.get(mood, {"arm": "erklaeren", "brauen": "neutral", "rest": "geschlossen"})
        elif typ == "news":
            sc["pose"] = {"down": {"arm": "erklaeren", "brauen": "besorgt", "rest": "geschlossen"},
                          "up": {"arm": "zeigen", "brauen": "neutral", "rest": "geschlossen"}}.get(d, {"arm": "erklaeren", "brauen": "neutral", "rest": "geschlossen"})
        else:
            sc["pose"] = {"arm": "winken", "brauen": "froh", "rest": "laecheln"}
            sc["nextAt"] = ls(0) + 0.1; sc["subAt"] = ls(1) + 0.05
        objs = sc.get("objects", [])
        for oi, o in enumerate(objs):
            at = o.get("at", 0)
            if oi == 0:
                o["appear"] = 0.35 if si == 0 else max(sc["swap"] + 0.2, ls(at) - 0.1); o["slideIn"] = False
            else:
                objs[oi - 1]["out"] = ls(at) - 0.15; o["appear"] = ls(at) + 0.09; o["slideIn"] = True
            if o["kind"] == "quote": o["countAt"] = ls(o.get("countLine", at)) + o.get("countDelay", 0.9)
            elif o["kind"] == "bars": o["countAt"] = o["appear"] + 0.16
            else: o["countAt"] = o["appear"] + 0.15
    tl = {"fps": FPS, "total": round(total, 3), "lines": lines, "scenes": scenes,
          "rms": [round(float(x), 3) for x in sm]}
    json.dump(tl, open(f"{out}/timeline.json", "w"), ensure_ascii=False)
    return tl

# ---------------------------------------------------------------- Bild
def build_page(st, tl, out):
    d = dt.date.fromisoformat(st["date"])
    st = dict(st); st["date_label"] = f"{WOCHENTAG[d.weekday()]}, {d.strftime('%d.%m.%Y')}"
    html = open(f"{TPL}/page.html").read()
    html = html.replace("/*STORY*/null", json.dumps(st, ensure_ascii=False)).replace("/*TL*/null", json.dumps(tl, ensure_ascii=False))
    html = html.replace("<!--RIG-->", open(f"{TPL}/assets/rig.svg").read())
    for f in ("tokens.css", "components", "fonts", "assets"):
        dst = f"{out}/{f}"
        if not os.path.exists(dst):
            (shutil.copytree if os.path.isdir(f"{TPL}/{f}") else shutil.copy)(f"{TPL}/{f}", dst)
    open(f"{out}/page.html", "w").write(html)

async def _frames(out, times, mp4=None):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        await pg.goto(f"file://{out}/page.html"); await pg.evaluate("window.READY")
        ff = None
        if mp4:
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), mp4 + ".part.mp4"],
                                  stdin=subprocess.PIPE)
        for i, t in enumerate(times):
            await pg.evaluate(f"setTime({t})")
            if ff: ff.stdin.write(await pg.screenshot(type="jpeg", quality=92))
            else: await pg.screenshot(path=f"{out}/still_{i:02d}.jpg", type="jpeg", quality=85)
        await b.close()
        if ff:
            ff.stdin.close()
            if ff.wait() == 0: os.rename(mp4 + ".part.mp4", mp4)
            else: raise SystemExit("ffmpeg-Fehler beim Rendern")

def stills(tl, out):
    ts = []
    for sc in tl["scenes"]:
        objs = sc.get("objects", [])
        if objs:
            for o in objs: ts.append(min(sc["end"], o["countAt"] + 1.3))
        else: ts.append(sc["end"] - 0.2)
    asyncio.run(_frames(out, ts))
    from PIL import Image
    ims = [Image.open(f"{out}/still_{i:02d}.jpg").resize((360, 640)) for i in range(len(ts))]
    cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (360 * cols, 640 * rows), "white")
    for i, im in enumerate(ims): sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
    sheet.save(f"{out}/sheet.jpg", quality=85)
    log(f"Kontrollbild: {out}/sheet.jpg")

def render(tl, out, k=None):
    k = k or max(2, min(6, os.cpu_count() or 2))
    N = int(tl["total"] * FPS); bounds = [round(N * i / k) for i in range(k + 1)]
    async def main():
        await asyncio.gather(*[_frames(out, [f / FPS for f in range(bounds[i], bounds[i + 1])], f"{out}/seg{i:02d}.mp4") for i in range(k)])
    asyncio.run(main())
    open(f"{out}/segs.txt", "w").write("".join(f"file 'seg{i:02d}.mp4'\n" for i in range(k)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{out}/segs.txt", "-c", "copy", f"{out}/video.mp4"], check=True)

# ---------------------------------------------------------------- Ton
def mix_audio(tl, out):
    sys.path.insert(0, f"{ROOT}/pipeline")
    import sound
    sound.make_mix(tl, f"{out}/voice.wav", f"{out}/mix.wav")

def main():
    path = sys.argv[1]; only_stills = "--stills" in sys.argv
    st = json.load(open(path))
    errs, warns = validate(st)
    for w in warns: log("WARNING:", w)
    for e in errs: log("ERROR:", e)
    if errs: sys.exit(1)
    name = os.path.splitext(os.path.basename(path))[0]
    out = f"{ROOT}/build/{name}"; os.makedirs(out, exist_ok=True)
    tl = build_timeline(st, out)
    log(f"Dauer: {tl['total']:.1f} s")
    if tl["total"] > 60.5: log("WARNING: länger als 60 s – Text kürzen")
    if tl["total"] < 40: log("WARNING: kürzer als 40 s")
    build_page(st, tl, out)
    stills(tl, out)
    if only_stills: return
    render(tl, out)
    mix_audio(tl, out)
    final = f"{out}/{name}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{out}/video.mp4", "-i", f"{out}/mix.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", final + ".part.mp4"], check=True)
    os.rename(final + ".part.mp4", final)
    log(f"Video: {final}")

if __name__ == "__main__":
    main()
