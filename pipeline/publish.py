"""Video rendern und an den GitHub-Workflow übergeben, der es auf YouTube hochlädt.

Aufruf: python3 pipeline/publish.py stories/2026-11-20_18.json [--now] [--draft] [--no-render]

1. rendert build/<name>/<name>.mp4 (ausser --no-render)
2. legt das MP4 auf den Branch `media` (main bleibt klein)
3. schreibt videos/<name>.json (Titel, Beschreibung, Tags, publishAt) und pusht main
   -> .github/workflows/publish.yml lädt das Video hoch (YouTube veröffentlicht es selbst zur Sendezeit)
4. wartet auf das Ergebnis im Branch `bot-logs` und gibt RESULT: OK / FAILED aus

--now    sofort öffentlich statt zur Sendezeit (wenn die Sendezeit näher als 10 Minuten ist, automatisch)
--draft  nur „nicht gelistet“ hochladen (Test)
"""
import datetime as dt, json, os, subprocess, sys, time
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = ZoneInfo("Europe/Zurich")
BOT = "-c user.name=daily-stockmarket-bot -c user.email=bot@users.noreply.github.com"
FOOTER = ("\n\nViermal täglich die wichtigsten Börsen- und Politik-News – um 6, 12, 18 und 24 Uhr.\n"
          "Keine Anlageberatung. Inhalte KI-gestützt erstellt, Zahlen aus den genannten Quellen.\n\n")


def sh(cmd, cwd=ROOT, check=True):
    r = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=True)
    if check and r.returncode:
        raise SystemExit(f"Befehl fehlgeschlagen: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()


def slot(date, edition):
    d = dt.date.fromisoformat(date)
    if edition == "24":
        local = dt.datetime.combine(d + dt.timedelta(days=1), dt.time(0, 0), TZ)
    else:
        local = dt.datetime.combine(d, dt.time(int(edition), 0), TZ)
    return local.astimezone(dt.timezone.utc)


def push_media(mp4, name):
    wt = "/tmp/ds-media"
    sh(f"rm -rf {wt}"); sh("git worktree prune")
    if sh("git ls-remote --heads origin media"):
        sh("git fetch -q --depth 1 origin media")
        sh(f"git worktree add -f {wt} FETCH_HEAD -B media-local")
    else:
        sh(f"git worktree add -f --detach {wt}")
        sh("git checkout -q --orphan media-local && git rm -rqf . && git clean -fdq", cwd=wt)
    os.makedirs(f"{wt}/videos", exist_ok=True)
    sh(f"cp {mp4} {wt}/videos/{name}.mp4")
    sh(f"git add videos/{name}.mp4 && git {BOT} commit -qm 'media {name}' && git push -q origin HEAD:media", cwd=wt)
    sh(f"git worktree remove --force {wt}")


def wait_result(name, run, timeout=420):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(15)
        if subprocess.run("git fetch -q --depth 1 origin bot-logs", cwd=ROOT, shell=True).returncode:
            continue
        r = subprocess.run(f"git show FETCH_HEAD:logs/{name}.txt", cwd=ROOT, shell=True, text=True, capture_output=True)
        if r.returncode == 0 and run in r.stdout:
            return r.stdout
    return None


def main():
    path = sys.argv[1]
    now, draft, render = "--now" in sys.argv, "--draft" in sys.argv, "--no-render" not in sys.argv
    st = json.load(open(path))
    name = os.path.splitext(os.path.basename(path))[0]
    mp4 = f"{ROOT}/build/{name}/{name}.mp4"
    if render:
        r = subprocess.run([sys.executable, f"{ROOT}/pipeline/make_video.py", path])
        if r.returncode: raise SystemExit("RESULT: FAILED (Rendern)")
    if not os.path.exists(mp4): raise SystemExit(f"RESULT: FAILED (fehlt: {mp4})")

    due = slot(st["date"], st["edition"])
    publish_at = None if (now or draft or due - dt.datetime.now(dt.timezone.utc) < dt.timedelta(minutes=10)) \
        else due.strftime("%Y-%m-%dT%H:%M:%SZ")
    run = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    tags = st.get("tags", [])
    hashtags = " ".join("#" + t.replace(" ", "") for t in (["Börse", "Aktien"] + tags[:3]))
    job = {"video": f"videos/{name}.mp4", "title": st["title"][:100],
           "description": st["description"].strip() + FOOTER + hashtags,
           "tags": tags + ["Börse", "Aktien", "Daily Stockmarket", "Börsennews"],
           "privacy": "unlisted" if draft else "public", "publishAt": publish_at, "run": run}

    sh("git pull -q --rebase origin main")
    push_media(mp4, name)
    os.makedirs(f"{ROOT}/videos", exist_ok=True); os.makedirs(f"{ROOT}/stories", exist_ok=True)
    json.dump(job, open(f"{ROOT}/videos/{name}.json", "w"), ensure_ascii=False, indent=1)
    if os.path.abspath(path) != f"{ROOT}/stories/{name}.json":
        sh(f"cp {path} stories/{name}.json")
    sh(f"git add stories/{name}.json videos/{name}.json && git {BOT} commit -qm 'Ausgabe {name}' && git push -q origin HEAD:main")
    print(f"Übergeben: videos/{name}.json · Veröffentlichung: {publish_at or 'sofort'}", flush=True)

    res = wait_result(name, run)
    if res is None:
        print("RESULT: UNKNOWN (keine Rückmeldung vom Workflow innerhalb von 7 Minuten)"); sys.exit(2)
    print(res)
    if "VIDEO_ID=" in res and "rc=0" in res:
        print("RESULT: OK")
    else:
        print("RESULT: FAILED"); sys.exit(1)


if __name__ == "__main__":
    main()
