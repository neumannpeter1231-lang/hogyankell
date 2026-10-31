#!/usr/bin/env python3
"""Felolvasás a szöveges posztokhoz (Gábor hangja), soronkénti időzítéssel.

Használat: python3 tools/szoveghang.py [post_id ...]
Kimenet: media/hang/<id>.mp3 és media/hang/hang.json ({id: [sorok kezdőidői mp-ben]})
"""
import base64, json, os, random, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "prototipus", "hogyankell.html")
OUT = os.path.join(ROOT, "media", "hang")


def secrets():
    env = {}
    for line in open(os.path.join(ROOT, ".secrets.env")):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v
    return env


def posts():
    s = open(APP, encoding="utf-8").read()
    for pid, lines in re.findall(r'\{id:"(\w+)", topic:"[^"]*", type:"text".*?lines:(\[.*?\]),\n', s, re.S):
        yield pid, [l.replace("*", "") for l in json.loads(lines)]


def main():
    env = secrets()
    only = set(sys.argv[1:])
    os.makedirs(OUT, exist_ok=True)
    idx_path = os.path.join(OUT, "hang.json")
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    for pid, lines in posts():
        if (only and pid not in only) or (pid in idx and not only):
            continue
        text, starts, pos = "", [], 0
        for l in lines:
            if text:
                text += " "
            starts.append(len(text))
            text += l
        url = (f"https://api.elevenlabs.io/v1/text-to-speech/{env.get('NARRATOR_VOICE_ID', env['GABOR_VOICE_ID'])}"
               "/with-timestamps?output_format=mp3_44100_96")
        req = urllib.request.Request(url, data=json.dumps({"text": text, "model_id": "eleven_v4", "voice_settings": random.choice([{"stability": 0.6, "similarity_boost": 0.75, "style": 0.15}, {"stability": 0.4, "similarity_boost": 0.75, "style": 0.35}])}).encode(),
                                     method="POST", headers={"xi-api-key": env["ELEVENLABS_API_KEY"],
                                                             "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.load(r)
        mp3 = os.path.join(OUT, pid + ".mp3")
        open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
        st = d["alignment"]["character_start_times_seconds"]
        idx[pid] = [round(st[k], 2) for k in starts]
        json.dump(idx, open(idx_path, "w"), indent=0)
        print(pid, "kész", round(d["alignment"]["character_end_times_seconds"][-1], 1), "mp")


if __name__ == "__main__":
    main()
