"""DecideDeck renderer — drop-in for assemble.build(items, out_path).

Pipeline: bot Item -> resolve per-option art via card.photo_for -> generate the
animated HTML per round (dd_anim.js) -> grab frames (dd_capture.js / Playwright)
-> Aria narration (dd_tts.py) -> ffmpeg mux (DecideDeck music bed + SFX, ducked
under the voice). Output: 1080x1920 H.264/AAC mp4 at out_path.

Everything downstream (meta, scheduler, youtube_upload, dashboard) is unchanged.
"""
from __future__ import annotations
import os, json, wave, math, tempfile, shutil, subprocess

import config
import card

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FPS = 30
STEP = 0.55                 # seconds per 3-2-1 number
CD = 3 * STEP               # countdown length (1.65s)
REVEAL_HOLD = 2.05          # hold after the reveal lands
MUSIC = os.path.join(ASSETS, "music_A.mp3")

WARM = ["coral", "tangerine", "sunset", "cherry", "amber", "fuchsia"]
SUITS_A = ["♠", "♦", "♣"]     # ♠ ♦ ♣
SUITS_B = ["♥", "♣", "♠"]     # ♥ ♣ ♠
# header + sub per format (all WYR in production, but robust to others)
HEAD = {
    "wyr": ("WOULD YOU RATHER", "PICK YOUR CARD"),
    "this_or_that": ("THIS OR THAT", "PICK A SIDE"),
    "rank": ("WHO WOULD WIN?", "PICK THE WINNER"),
    "trivia": ("GUESS THE ANSWER", "PICK ONE"),
    "higher_lower": ("WHICH IS BIGGER?", "PICK ONE"),
}
NODE_PATH = os.getenv("DD_NODE_PATH", "/home/claude/.npm-global/lib/node_modules")


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _fit(p):
    # Square cartoon art / photos fill the card (cover); wide brand logos show
    # whole (contain) so they aren't cropped to a sliver.
    p = p.replace("\\", "/")
    return "cover" if ("/assets/art/" in p or "/images/auto/" in p) else "contain"


def _wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()


def _narration(it, idx=0, total=1):
    # Use the bot's own phrasing so the full question is read, not just the
    # "Would you rather" lead-in (item.prompt is only the prefix).
    import assemble
    try:
        q, _ = assemble._spoken(it, idx, total)
        q = (q or "").strip()
        if q:
            return q
    except Exception:
        pass
    return f"Would you rather {it.a}, or {it.b}?"


def build(items, out_path: str, background: str | None = None) -> str:
    import content
    if isinstance(items, content.Item):
        items = [items]
    work = tempfile.mkdtemp(prefix="dd_")
    frames = os.path.join(work, "frames")
    os.makedirs(frames, exist_ok=True)
    voice = getattr(config, "EDGE_VOICE", "en-US-AriaNeural")
    rate = getattr(config, "EDGE_RATE", "+40%")
    # In CI, playwright is installed into the repo's local node_modules (node
    # resolves that first), so only set NODE_PATH when the dev path actually exists.
    env = dict(os.environ)
    if os.path.isdir(NODE_PATH):
        env["NODE_PATH"] = NODE_PATH

    rounds, durs, vls, voices = [], [], [], []
    for i, it in enumerate(items):
        a_img = card.photo_for(it.a, getattr(it, "a_art", "") or None)
        b_img = card.photo_for(it.b, getattr(it, "b_art", "") or None)
        if not (a_img and b_img):
            raise RuntimeError(f"round {i}: missing art for "
                               f"{it.a!r}({bool(a_img)}) / {it.b!r}({bool(b_img)})")
        # narration -> wav -> duration
        mp3 = os.path.join(work, f"v{i}.mp3")
        wav = os.path.join(work, f"v{i}.wav")
        subprocess.run(["python3", os.path.join(HERE, "dd_tts.py"),
                        mp3, voice, rate, _narration(it, i, len(items))], check=True, env=env)
        subprocess.run(["ffmpeg", "-y", "-i", mp3, "-ac", "1", "-ar", "44100", wav],
                       capture_output=True)
        d = _wav_dur(wav); durs.append(d); voices.append(wav)
        vl = round(_clamp(d + 0.55, 1.6, 4.6), 2); vls.append(vl)
        head, sub = HEAD.get(it.fmt, HEAD["wyr"])
        rounds.append({
            "pal": WARM[i % len(WARM)], "head": head, "sub": sub,
            "la": it.a, "lb": it.b, "imgA": a_img, "imgB": b_img,
            "fitA": _fit(a_img), "fitB": _fit(b_img),
            "sa": SUITS_A[i % 3], "sb": SUITS_B[i % 3],
            "pa": int(it.a_pct), "pb": int(it.b_pct),
            "win": "A" if it.a_pct >= it.b_pct else "B", "vl": vl,
        })

    rj = os.path.join(work, "rounds.json")
    with open(rj, "w") as f:
        json.dump(rounds, f)
    subprocess.run(["node", os.path.join(HERE, "dd_anim.js"), rj, work],
                   check=True, env=env)

    # capture each round into one continuous frame sequence
    offset = 0
    round_start = []
    for i, vl in enumerate(vls):
        secs = round(vl + CD + REVEAL_HOLD, 2)
        round_start.append(offset / FPS)
        subprocess.run(["node", os.path.join(HERE, "dd_capture.js"),
                        os.path.join(work, f"round_{i}.html"), frames,
                        str(FPS), str(secs), "1", str(offset)], check=True, env=env)
        offset += round(secs * FPS)
    total = offset / FPS

    # audio cue times
    ticks, dings, whooshes, pops, vcues, ducks = [], [], [], [], [], []
    for i, vl in enumerate(vls):
        rs = round_start[i]
        for k in range(3):
            ticks.append(round(rs + vl + k * STEP, 3))
        dings.append(round(rs + vl + CD, 3))
        whooshes.append(round(rs + vl + CD, 3))
        pops.append(round(rs + vl + CD + 0.55, 3))
        vs = round(rs + 0.15, 3)
        vcues.append((voices[i], vs))
        ducks.append((rs, round(vs + durs[i] + 0.2, 3)))

    _mux(frames, vcues, ticks, dings, whooshes, pops, ducks, total, out_path)
    shutil.rmtree(work, ignore_errors=True)
    if not (os.path.exists(out_path) and os.path.getsize(out_path) > 10000):
        raise RuntimeError("dd_render produced no output")
    return out_path


def _mux(frames, vcues, ticks, dings, whooshes, pops, ducks, total, out_path):
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(frames, "f%05d.png"),
           "-stream_loop", "-1", "-i", MUSIC,
           "-i", os.path.join(ASSETS, "tick.wav"), "-i", os.path.join(ASSETS, "ding.wav"),
           "-i", os.path.join(ASSETS, "whoosh.wav"), "-i", os.path.join(ASSETS, "pop.wav")]
    v0 = 6
    for wav, _ in vcues:
        cmd += ["-i", wav]

    fc, labels = [], []

    def emit(src, cues, vol, tag):
        n = len(cues)
        fc.append(f"[{src}:a]asplit={n}" + "".join(f"[{tag}s{i}]" for i in range(n)))
        for i, c in enumerate(cues):
            ms = int(c * 1000)
            fc.append(f"[{tag}s{i}]adelay={ms}|{ms},volume={vol}[{tag}{i}]")
            labels.append(f"{tag}{i}")

    emit(2, ticks, 0.9, "t")
    emit(3, dings, 0.9, "d")
    emit(4, whooshes, 0.5, "w")
    emit(5, pops, 0.5, "p")
    for i, (wav, vs) in enumerate(vcues):
        ms = int(vs * 1000)
        fc.append(f"[{v0+i}:a]adelay={ms}|{ms},volume=1.5[v{i}]")
        labels.append(f"v{i}")

    duck = "+".join(f"between(t,{s},{e})" for s, e in ducks) or "0"
    fc.append(f"[1:a]volume='if(gt({duck},0),0.16,0.5)':eval=frame[mus]")
    mix = "[mus]" + "".join(f"[{l}]" for l in labels)
    fc.append(f"{mix}amix=inputs={len(labels)+1}:normalize=0[mx]")
    fc.append(f"[mx]afade=t=out:st={total-0.4:.2f}:d=0.4[aout]")

    cmd += ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[aout]",
            "-t", f"{total:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg mux failed:\n" + r.stderr[-1500:])


if __name__ == "__main__":
    # standalone smoke test: build a real video from the bot's own content
    import content, datetime
    date = datetime.date.today().isoformat()
    items = content.several("wyr", date, 3)
    if getattr(config, "ART_REQUIRED", True):
        items = content.ensure_art(items, "wyr")
    for i, it in enumerate(items, 1):
        print(f"  round {i}: {it.a} ({it.a_pct}%) vs {it.b} ({it.b_pct}%)")
    out = os.path.join(HERE, "output", "dd_sample.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    build(items, out)
    print("built", out, os.path.getsize(out) // 1024, "KB")
