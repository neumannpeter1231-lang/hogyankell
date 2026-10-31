#!/usr/bin/env python3
"""Felolvasás ElevenLabs API-val, betűszintű időzítéssel.

Használat: python3 tools/hang.py anyag/sorozat1.json [video_id ...]
Kimenet videónként: anyag/<id>/hang.mp3 és anyag/<id>/align.json
A kulcsok a .secrets.env fájlban vannak (ELEVENLABS_API_KEY, GABOR_VOICE_ID).
"""
import base64, json, os, random, subprocess, sys, urllib.request

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

# Gemini-hangok (Péter választása 2026-10-31: Charon, Orus, Fenrir férfi; Kore, Aoede női; a Sulafat kiesett).
# Ezek a "hang" mezővel választhatók, pl. "gemini_charon". Jelenetenként külön felolvasás -> pontos jelenethatárok.
GEMINI_VOICES = {"gemini_charon": "Charon", "gemini_orus": "Orus", "gemini_fenrir": "Fenrir",
                 "gemini_kore": "Kore", "gemini_aoede": "Aoede"}
GEMINI_TTS_MODEL = "gemini-3.8-flash-tts"
GEMINI_STYLE = ""  # a modell minden előtagot felolvas (magyart és angolt is), ezért csak a sima szöveg megy


def pick(video):
    if video.get("hang") in PROFILES or video.get("hang") in GEMINI_VOICES:
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


def gemini_scene(text, voice, env, wav):
    """Egy jelenet felolvasása Gemini TTS-sel -> wav fájl."""
    body = {"contents": [{"parts": [{"text": GEMINI_STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_TTS_MODEL}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"x-goog-api-key": env["GEMINI_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    raw = base64.b64decode(part["data"])
    tmp = wav + ".raw"
    open(tmp, "wb").write(raw)
    if raw[:4] == b"RIFF":
        src = ["-i", tmp]
    else:  # nyers 16 bites PCM
        rate = part.get("mimeType", "").split("rate=")[-1].split(";")[0]
        src = ["-f", "s16le", "-ar", rate if rate.isdigit() else "24000", "-ac", "1", "-i", tmp]
    # elejéről és végéről a csend levágása, hogy a jelenethatár pontos legyen
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *src, "-af", trim, "-ar", "44100", "-ac", "1", wav],
                   check=True)
    os.remove(tmp)


def char_weight(c):
    if c in ".!?":
        return 5.0
    if c in ",:;–-":
        return 2.5
    if c.isspace():
        return 0.6
    return 1.0


def gemini_video(video, voice, env, out):
    """Jelenetenkénti Gemini-felolvasás + betűszintű időzítés a jeleneten belüli arányos becsléssel.
    A kimenet ugyanolyan align.json, mint az ElevenLabsé, így az osszerak.py változatlanul használja."""
    gap = 0.35  # szünet a jelenetek között (mp)
    wavs, durs = [], []
    for i, sc in enumerate(video["scenes"]):
        w = os.path.join(out, f"_s{i:02d}.wav")
        gemini_scene(sc["text"], voice, env, w)
        wavs.append(w)
        durs.append(float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", w], capture_output=True, text=True).stdout))
    # összefűzés szünetekkel
    silence = os.path.join(out, "_gap.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", str(gap), silence], check=True)
    lst = os.path.join(out, "_list.txt")
    with open(lst, "w") as f:
        for i, w in enumerate(wavs):
            f.write(f"file '{w}'\n")
            if i < len(wavs) - 1:
                f.write(f"file '{silence}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-b:a", "128k", os.path.join(out, "hang.mp3")], check=True)
    # betűszintű időzítés
    text, offsets, chars, st, en = "", [], [], [], []
    t = 0.0
    for i, sc in enumerate(video["scenes"]):
        seg = sc["text"]
        if text:
            text += " "; chars.append(" "); st.append(t - gap); en.append(t)
        start = len(text)
        ws = [char_weight(c) for c in seg]
        tot = sum(ws)
        acc = 0.0
        for c, wgt in zip(seg, ws):
            chars.append(c)
            st.append(t + durs[i] * acc / tot)
            acc += wgt
            en.append(t + durs[i] * acc / tot)
        text += seg
        offsets.append({"start": start, "end": start + len(seg)})
        t += durs[i] + gap
    for p in wavs + [silence, lst]:
        os.remove(p)
    return text, offsets, {"characters": chars, "character_start_times_seconds": st,
                           "character_end_times_seconds": en}


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
        if name in GEMINI_VOICES:
            text, offsets, a = gemini_video(v, GEMINI_VOICES[name], env, out)
            json.dump({"text": text, "scenes": offsets, "alignment": a, "hang": name},
                      open(os.path.join(out, "align.json"), "w"), ensure_ascii=False)
            print(v["id"], name, "kész", round(a["character_end_times_seconds"][-1], 1), "mp")
            continue
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
