#!/usr/bin/env python3
"""Magyarázó videó összerakása: jelenetképek + felolvasott hang -> 9:16 mp4 felirattal.

Használat:
  python3 tools/make_explainer.py spec.json

spec.json:
{
  "audio": "anyag/horgony/hang.mp3",
  "out": "media/horgony.mp4",          # mellé kerül a poszter is: media/horgony.jpg
  "scenes": [
    {"img": "anyag/horgony/01.png", "text": "Tapasztalt ingatlanügynököket kértek meg ..."},
    ...
  ]
}
A jelenetek szövegei együtt adják ki a teljes felolvasott szöveget, sorrendben.
Az időzítés a szöveg hosszából becsül, és a hangban talált szünetekhez igazítja
a mondathatárokat (nincs szükség külön átiratra).
"""
import json, os, re, subprocess, sys, tempfile

W, H, FPS = 720, 1280, 30
FONT = "Inter Display Black"          # telepített betűtípus; ASS-ben a családnév kell
CAPTION_MAX_CHARS = 18          # egy feliratblokk max. hossza
SNAP_TOL = 0.9                  # mondathatár max. ennyit csúszhat egy szünethez (mp)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit("hiba: " + " ".join(cmd[:4]))
    return r


def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def silences(path):
    """Szünetek közepei a hangban (mp)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                        "silencedetect=noise=-33dB:d=0.18", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [((s + e) / 2, e - s) for s, e in zip(starts, ends)]


def weight(text):
    """Kb. kimondási idő arányosan: betűk + szünet az írásjeleknél."""
    letters = len(re.sub(r"[^\wáéíóöőúüűÁÉÍÓÖŐÚÜŰ]", "", text))
    pauses = len(re.findall(r"[.!?]", text)) * 6 + len(re.findall(r"[,:;–-]", text)) * 3
    return letters + pauses


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def plan(scenes, total, sil):
    """Mondatok kezdő/záró ideje, szünetekhez igazítva."""
    sents = []  # (scene_idx, text)
    for i, sc in enumerate(scenes):
        for s in sentences(sc["text"]):
            sents.append((i, s))
    # a felvétel elején/végén lévő csend
    lead = sil[0][0] + sil[0][1] / 2 if sil and sil[0][0] - sil[0][1] / 2 < 0.05 else 0.0
    tail = total
    if sil and abs((sil[-1][0] + sil[-1][1] / 2) - total) < 0.1:
        tail = sil[-1][0] - sil[-1][1] / 2
    ws = [weight(t) for _, t in sents]
    span = tail - lead
    bounds = [lead]
    acc = 0
    for w in ws[:-1]:
        acc += w
        bounds.append(lead + span * acc / sum(ws))
    bounds.append(tail)
    # belső határok igazítása a legközelebbi, még nem használt szünethez
    inner = [m for m, d in sil if lead + 0.2 < m < tail - 0.2]
    used = set()
    for k in range(1, len(bounds) - 1):
        best = None
        for j, m in enumerate(inner):
            if j in used or m <= bounds[k - 1] + 0.3:
                continue
            if abs(m - bounds[k]) <= SNAP_TOL and (best is None or abs(m - bounds[k]) < abs(inner[best] - bounds[k])):
                best = j
        if best is not None:
            used.add(best)
            bounds[k] = inner[best]
    out = []
    for k, (i, t) in enumerate(sents):
        out.append({"scene": i, "text": t, "start": bounds[k], "end": bounds[k + 1]})
    return out


def chunks(text):
    words = text.split()
    res, cur = [], []
    for w in words:
        cand = " ".join(cur + [w])
        if cur and (len(cand) > CAPTION_MAX_CHARS or re.search(r"[,.!?:;]$", cur[-1])):
            res.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        res.append(" ".join(cur))
    return res


def ts(t):
    t = max(0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_file(sents, path):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,6,2,2,50,50,330,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for s in sents:
        parts = chunks(s["text"])
        ws = [weight(p) for p in parts]
        t = s["start"]
        dur = s["end"] - s["start"]
        for p, w in zip(parts, ws):
            d = dur * w / sum(ws)
            txt = re.sub(r"[.,;:]+$", "", p).replace("{", "(").replace("}", ")")
            # kis "pattanás" megjelenéskor
            fx = r"{\fscx86\fscy86\t(0,90,\fscx100\fscy100)}"
            lines.append(f"Dialogue: 0,{ts(t)},{ts(t + d)},Cap,,0,0,0,,{fx}{txt}")
            t += d
    open(path, "w", encoding="utf-8").write(head + "\n".join(lines) + "\n")


def scene_clip(img, dur, idx, out):
    """Ken Burns: felváltva lassú ráközelítés / távolodás, enyhe oldalirányú úszással."""
    frames = max(1, round(dur * FPS))
    z0, z1 = (1.0, 1.12) if idx % 2 == 0 else (1.12, 1.0)
    dx = [0.0, 0.04, -0.04][idx % 3]
    z = f"({z0}+({z1}-{z0})*on/{frames})"
    x = f"(iw-iw/zoom)/2+iw*{dx}*on/{frames}"
    y = "(ih-ih/zoom)/2"
    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
    run(["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", out])


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(spec_path))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    audio, out = P(spec["audio"]), P(spec["out"])
    scenes = spec["scenes"]
    total = duration(audio)
    sil = silences(audio)
    sents = plan(scenes, total, sil)

    # jelenetek időtartama: első mondatuk kezdetétől a következő jelenet első mondatáig
    starts = []
    for i in range(len(scenes)):
        own = [s for s in sents if s["scene"] == i]
        starts.append(own[0]["start"] if own else None)
    starts[0] = 0.0
    edges = starts + [total]
    with tempfile.TemporaryDirectory() as tmp:
        lst = []
        for i, sc in enumerate(scenes):
            d = edges[i + 1] - edges[i]
            clip = os.path.join(tmp, f"s{i:02d}.mp4")
            scene_clip(P(sc["img"]), d, i, clip)
            lst.append(f"file '{clip}'")
        open(os.path.join(tmp, "list.txt"), "w").write("\n".join(lst) + "\n")
        ass = os.path.join(tmp, "cap.ass")
        ass_file(sents, ass)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"),
             "-i", audio, "-vf", f"ass={ass}", "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-profile:v", "main",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-c:a", "aac", "-b:a", "96k", "-shortest", out])
    poster = os.path.splitext(out)[0] + ".jpg"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", P(scenes[0]["img"]), "-vf",
         f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}", "-frames:v", "1", "-q:v", "4", poster])
    print(json.dumps({"out": out, "poster": poster, "duration": round(total, 2),
                      "scenes": [round(edges[i + 1] - edges[i], 2) for i in range(len(scenes))],
                      "silences": len(sil)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
