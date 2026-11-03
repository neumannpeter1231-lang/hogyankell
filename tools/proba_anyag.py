#!/usr/bin/env python3
"""Próba-anyag a gyártósorhoz, API és költség nélkül (2026-11-03).

Használat: python3 tools/proba_anyag.py anyag/funfact1.json [video_id ...]
Videónként anyag/<id>/01.png… helyettesítő képeket, egy sípszó-hangot (hang.mp3) és a hozzá illő
align.json-t készít, pontosan olyan formában, mint a tools/hang.py és a tools/kepek.py. Így a teljes
gyártósor (összevágás, kicsinyítés, posztok, build, teszt) kipróbálható Gemini- és ElevenLabs-kulcs nélkül.
A próbavideót SOHA ne olvaszd be élesbe: a gyártósor a PR címében és leírásában is jelzi, hogy próba.
"""
import importlib.util, json, os, subprocess, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAR_PER_MP = 14.5
COLORS = [(224, 51, 143), (31, 181, 168), (242, 194, 48), (90, 70, 160), (40, 120, 200), (230, 120, 40)]

_spec = importlib.util.spec_from_file_location("hang", os.path.join(ROOT, "tools", "hang.py"))
hang = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(hang)


def image(path, i, title):
    img = Image.new("RGB", (768, 1365), COLORS[i % len(COLORS)])
    d = ImageDraw.Draw(img)
    for k in range(0, 1365, 60):
        d.line([(0, k), (768, k + 300)], fill=(255, 255, 255), width=3)
    d.rectangle([180, 520, 588, 840], fill=(14, 17, 22))
    d.text((210, 560), f"PROBA {i + 1}", fill=(242, 194, 48))
    d.text((210, 600), title[:24], fill=(255, 255, 255))
    img.save(path)


def audio_and_align(video, out):
    """Jelenetenként a becsült hosszú halk sípszó, a jelenetek között 0,35 mp csend – a hang.py gemini_video() formátumában."""
    gap = 0.35
    durs = [max(1.5, len(sc["text"]) / KAR_PER_MP) for sc in video["scenes"]]
    parts = []
    for i, dur in enumerate(durs):
        parts.append(f"sine=frequency={330 + 40 * i}:sample_rate=44100:duration={dur:.2f},volume=0.08")
        if i < len(durs) - 1:
            parts.append(f"anullsrc=r=44100:cl=mono:d={gap}")
    inputs = []
    for p in parts:
        inputs += ["-f", "lavfi", "-i", p]
    n = len(parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
                    "".join(f"[{k}:a]" for k in range(n)) + f"concat=n={n}:v=0:a=1,aformat=channel_layouts=mono[a]",
                    "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "64k", os.path.join(out, "hang.mp3")], check=True)
    text, offsets, chars, st, en, t = "", [], [], [], [], 0.0
    for i, sc in enumerate(video["scenes"]):
        seg = sc["text"]
        if text:
            text += " "; chars.append(" "); st.append(t - gap); en.append(t)
        start = len(text)
        ws = [hang.char_weight(c) for c in seg]
        tot, acc = sum(ws), 0.0
        for c, w in zip(seg, ws):
            chars.append(c); st.append(t + durs[i] * acc / tot); acc += w; en.append(t + durs[i] * acc / tot)
        text += seg
        offsets.append({"start": start, "end": start + len(seg)})
        t += durs[i] + gap
    json.dump({"text": text, "scenes": offsets, "hang": "proba",
               "alignment": {"characters": chars, "character_start_times_seconds": st, "character_end_times_seconds": en}},
              open(os.path.join(out, "align.json"), "w"), ensure_ascii=False)
    return t - gap


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    only = set(sys.argv[2:])
    for v in spec["videos"]:
        if only and v["id"] not in only:
            continue
        out = os.path.join(ROOT, "anyag", v["id"])
        os.makedirs(out, exist_ok=True)
        for i in range(len(v["scenes"])):
            p = os.path.join(out, f"{i + 1:02d}.png")
            if not os.path.exists(p):
                image(p, i, v["title"])
        if not os.path.exists(os.path.join(out, "hang.mp3")):
            print(v["id"], "próba-anyag kész,", round(audio_and_align(v, out), 1), "mp")


if __name__ == "__main__":
    main()
