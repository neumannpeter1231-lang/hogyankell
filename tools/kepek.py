#!/usr/bin/env python3
"""Jelenetképek generálása a Gemini API-val (Nano Banana 2.1), teljesen automatikusan.

Használat: python3 tools/kepek.py anyag/sorozat3.json [video_id ...]
Kimenet: anyag/<id>/01.png, 02.png, ... (a már meglévőket kihagyja)
A kulcs a .secrets.env fájlban van (GEMINI_API_KEY). Kb. 0,067 $ / kép.
A prompt: jelenet "prompt" mezője + a sorozat "style" mezője (a megszokott stílus).
"""
import base64, json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "gemini-nano-banana-2.1"


def secrets():
    env = {}
    for line in open(os.path.join(ROOT, ".secrets.env")):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env


def generate(prompt, key):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.load(r)
            for part in d["candidates"][0]["content"]["parts"]:
                if "inlineData" in part:
                    return base64.b64decode(part["inlineData"]["data"])
            raise RuntimeError("nincs kép a válaszban: " + json.dumps(d)[:300])
        except urllib.error.HTTPError as e:
            msg = e.read()[:300]
            if e.code in (429, 500, 503) and attempt < 2:
                time.sleep(10 * (attempt + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    only = set(sys.argv[2:])
    key = secrets()["GEMINI_API_KEY"]
    style = spec["style"]
    for v in spec["videos"]:
        if only and v["id"] not in only:
            continue
        out = os.path.join(ROOT, "anyag", v["id"])
        os.makedirs(out, exist_ok=True)
        for i, sc in enumerate(v["scenes"]):
            path = os.path.join(out, f"{i+1:02d}.png")
            if os.path.exists(path):
                continue
            img = generate(sc["prompt"] + ". " + style, key)
            tmp = path + ".tmp"
            open(tmp, "wb").write(img)
            os.replace(tmp, path)
            print(v["id"], f"{i+1:02d}.png", len(img) // 1024, "KB")


if __name__ == "__main__":
    main()
