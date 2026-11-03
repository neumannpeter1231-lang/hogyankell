#!/usr/bin/env python3
"""„Tudtad?” (fun fact) posztok beírása az appba egy forgatókönyv-JSON alapján.

Használat: python3 tools/funfact.py anyag/funfact1.json [anyag/funfact2.json ...]

Az appban a /* FUNFACT:BEGIN */ ... /* FUNFACT:END */ közötti részt teljesen újraírja,
ezért bármikor újra futtatható. Ha van már media/<id>.mp4, videós posztot ír, különben
szöveges posztot (a jelenetek 'line' mezőiből), így a fun fact a videó elkészülte előtt
is megjelenik, és a videó elkészülte után egy újrafuttatással át is vált videóra.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "prototipus", "hogyankell.html")
BEGIN, END = "/* FUNFACT:BEGIN */", "/* FUNFACT:END */"


def js(o):
    return json.dumps(o, ensure_ascii=False)


def post(v):
    vid = v["id"]
    has_video = os.path.exists(os.path.join(ROOT, "media", vid + ".mp4"))
    p = {"id": "f_" + vid, "topic": v.get("topic", "Tudtad?"), "fun": True,
         "title": v["title"], "tags": v["tags"], "lesson": v["lesson"]}
    if has_video:
        p.update(type="video", src=f"media/{vid}.mp4", poster=f"media/{vid}.jpg")
    else:
        p.update(type="text", icon=v.get("icon", "search"), lines=[s.get("line") or s["text"] for s in v["scenes"]])
    for k in ("poll", "check"):
        p[k] = v[k]
    p["deeper"] = v["deeper"]
    p["source"] = v["source"]
    return p


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    posts, qvar = [], {}
    for f in sys.argv[1:]:
        spec = json.load(open(f, encoding="utf-8"))
        for v in spec["videos"]:
            if not v.get("lesson") or not v.get("source", {}).get("label"):
                sys.exit(f"{v['id']}: hiányzik a tanulság vagy a forrás – fun fact nem mehet ki nélküle")
            posts.append(post(v))
            if v.get("qvar"):
                qvar["f_" + v["id"]] = v["qvar"]
    block = (BEGIN + "\n/* Ezt a részt a tools/funfact.py írja, kézzel ne szerkeszd. */\n"
             + "const FUN_POSTS = [\n" + ",\n".join(" " + js(p) for p in posts) + "\n];\n"
             + "const FUN_QVAR = " + js(qvar) + ";\n" + END)
    s = open(APP, encoding="utf-8").read()
    if BEGIN not in s:
        sys.exit("Nincs FUNFACT jelölő az appban.")
    s = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: block, s, count=1, flags=re.S)
    open(APP, "w", encoding="utf-8").write(s)
    kinds = [("videó" if p["type"] == "video" else "szöveg") + ":" + p["id"] for p in posts]
    print("beírva:", ", ".join(kinds))


if __name__ == "__main__":
    main()
