#!/usr/bin/env python3
"""Felolvasás ElevenLabs API-val, betűszintű időzítéssel.

Használat: python3 tools/hang.py anyag/sorozat1.json [video_id ...]
Kimenet videónként: anyag/<id>/hang.mp3 és anyag/<id>/align.json
A kulcsok a .secrets.env fájlban vannak (ELEVENLABS_API_KEY, GABOR_VOICE_ID).
"""
import base64, json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def secrets():
    env = {}
    for line in open(os.path.join(ROOT, ".secrets.env")):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env


def tts(text, env):
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{env['GABOR_VOICE_ID']}"
           "/with-timestamps?output_format=mp3_44100_128")
    body = json.dumps({"text": text, "model_id": "eleven_v4"}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": env["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def build(video):
    """Teljes szöveg címkékkel + az egyes jelenetek kezdő karakterpozíciója."""
    parts, offsets, pos = [], [], 0
    for sc in video["scenes"]:
        chunk = (sc.get("tag", "") + " " if sc.get("tag") else "")
        start = pos + len(chunk)
        chunk += sc["text"]
        offsets.append({"start": start, "end": start + len(sc["text"])})
        parts.append(chunk)
        pos += len(chunk) + 1
    return " ".join(parts), offsets


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    only = set(sys.argv[2:])
    env = secrets()
    for v in spec["videos"]:
        if only and v["id"] not in only:
            continue
        out = os.path.join(ROOT, "anyag", v["id"])
        os.makedirs(out, exist_ok=True)
        if os.path.exists(os.path.join(out, "hang.mp3")):
            print(v["id"], "már kész"); continue
        text, offsets = build(v)
        d = tts(text, env)
        open(os.path.join(out, "hang.mp3"), "wb").write(base64.b64decode(d["audio_base64"]))
        a = d["alignment"]
        json.dump({"text": text, "scenes": offsets, "alignment": a}, open(os.path.join(out, "align.json"), "w"),
                  ensure_ascii=False)
        print(v["id"], "kész", round(a["character_end_times_seconds"][-1], 1), "mp")


if __name__ == "__main__":
    main()
