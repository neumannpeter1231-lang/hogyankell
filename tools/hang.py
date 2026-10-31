#!/usr/bin/env python3
"""Felolvasás ElevenLabs API-val, betűszintű időzítéssel.

Használat: python3 tools/hang.py anyag/sorozat1.json [video_id ...]
Kimenet videónként: anyag/<id>/hang.mp3 és anyag/<id>/align.json
A kulcsok a .secrets.env fájlban vannak (ELEVENLABS_API_KEY, GABOR_VOICE_ID).
"""
import base64, json, os, random, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Péter kérése: a narráció ne legyen egyhangú. Arányok: 1/2 Gábor, 1/6-1/6-1/6 Vera (tanító / közepes / élénk).
# Egy videó a forgatókönyvben "hang" mezővel kötelezően megkaphat egy profilt (kontextusfüggő választás),
# pl. komoly, biztonsági témánál "vera_tanito", meglepő kísérletnél "vera_elenk".
GABOR, VERA = "7B7mSWflzRSaO1yGeJH6", "xjlfQQ3ynqiEyRpArrT8"
PROFILES = {
    "gabor":        {"voice": GABOR, "tags": True,  "vs": None},
    "vera_tanito":  {"voice": VERA,  "tags": False, "vs": {"stability": 0.6, "similarity_boost": 0.75, "style": 0.15}},
    "vera_kozepes": {"voice": VERA,  "tags": True,  "vs": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.3}},
    "vera_elenk":   {"voice": VERA,  "tags": True,  "vs": None},
}
WEIGHTS = {"gabor": 3, "vera_tanito": 1, "vera_kozepes": 1, "vera_elenk": 1}


def pick(video):
    if video.get("hang") in PROFILES:
        return video["hang"]
    return random.choices(list(WEIGHTS), weights=list(WEIGHTS.values()))[0]


def secrets():
    env = {}
    for line in open(os.path.join(ROOT, ".secrets.env")):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env


def tts(text, env, prof):
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{prof['voice']}"
           "/with-timestamps?output_format=mp3_44100_128")
    body = {"text": text, "model_id": "eleven_v4"}
    if prof["vs"]:
        body["voice_settings"] = prof["vs"]
    body = json.dumps(body).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": env["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def build(video, tags):
    """Teljes szöveg címkékkel + az egyes jelenetek kezdő karakterpozíciója."""
    parts, offsets, pos = [], [], 0
    for sc in video["scenes"]:
        chunk = (sc.get("tag", "") + " " if tags and sc.get("tag") else "")
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
        name = pick(v)
        prof = PROFILES[name]
        text, offsets = build(v, prof["tags"])
        d = tts(text, env, prof)
        open(os.path.join(out, "hang.mp3"), "wb").write(base64.b64decode(d["audio_base64"]))
        a = d["alignment"]
        json.dump({"text": text, "scenes": offsets, "alignment": a, "hang": name}, open(os.path.join(out, "align.json"), "w"),
                  ensure_ascii=False)
        print(v["id"], name, "kész", round(a["character_end_times_seconds"][-1], 1), "mp")


if __name__ == "__main__":
    main()
