#!/usr/bin/env python3
"""Sorozat összevágása: anyag/<id>/01.png..NN.png + hang.mp3 + align.json -> media/<id>.mp4

Használat: python3 tools/osszerak.py anyag/sorozat1.json [id ...]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    only = set(sys.argv[2:])
    for v in spec["videos"]:
        if only and v["id"] not in only:
            continue
        d = os.path.join(ROOT, "anyag", v["id"])
        imgs = [os.path.join(d, f"{i+1:02d}.png") for i in range(len(v["scenes"]))]
        if not all(os.path.exists(p) for p in imgs) or not os.path.exists(os.path.join(d, "align.json")):
            print(v["id"], "hiányos, kihagyva"); continue
        sp = {"audio": os.path.join(d, "hang.mp3"), "align": os.path.join(d, "align.json"),
              "out": os.path.join(ROOT, "media", v["id"] + ".mp4"),
              "scenes": [{"img": p, "text": ""} for p in imgs]}
        sf = os.path.join(d, "spec.json")
        json.dump(sp, open(sf, "w"), ensure_ascii=False, indent=1)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_explainer.py"), sf],
                           capture_output=True, text=True)
        print(v["id"], "OK" if r.returncode == 0 else "HIBA " + r.stderr[-300:])


if __name__ == "__main__":
    main()
