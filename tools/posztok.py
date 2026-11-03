#!/usr/bin/env python3
"""Videós posztok beszúrása a prototípusba egy sorozat-JSON alapján.

Használat: python3 tools/posztok.py anyag/sorozat1.json
Csak azokat szúrja be, amelyekhez már van media/<id>.mp4, és még nincsenek bent.
A forgatókönyv "qvar" mezőjét (párbaj-kérdésváltozatok) a QVAR-ba is beírja (2026-11-03), ha még nincs bent.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "prototipus", "hogyankell.html")


def js(o):
    return json.dumps(o, ensure_ascii=False)


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    s = open(APP, encoding="utf-8").read()
    anchor = " {id:\"p2\", topic:\"Pszichológia\", type:\"video\""
    hanchor = "const HABIT = {\n"
    added = []
    for v in spec["videos"]:
        pid = "v_" + v["id"]
        if f'id:"{pid}"' in s or not os.path.exists(os.path.join(ROOT, "media", v["id"] + ".mp4")):
            continue
        post = (f' {{id:"{pid}", topic:{js(v["topic"])}, type:"video", src:"media/{v["id"]}.mp4", poster:"media/{v["id"]}.jpg",\n'
                f'  title:{js(v["title"])}, tags:{js(v["tags"])},\n'
                f'  poll:{{q:{js(v["poll"]["q"])}, o:{js(v["poll"]["o"])}, a:{v["poll"]["a"]}, why:{js(v["poll"]["why"])}}},\n'
                f'  check:{{q:{js(v["check"]["q"])}, o:{js(v["check"]["o"])}, a:{v["check"]["a"]}, why:{js(v["check"]["why"])}}},\n'
                f'  deeper:{js(v["deeper"])},\n'
                f'  source:{{label:{js(v["source"]["label"])}, url:{js(v["source"]["url"])}}}}},\n')
        s = s.replace(anchor, post + anchor, 1)
        h = v["habit"]
        s = s.replace(hanchor, hanchor + f'  {pid}:{{text:{js(h["text"])}, time:{js(h["time"])}, days:{h["days"]}}},\n', 1)
        added.append(pid)
    # kérdésváltozatok a QVAR-ba (az app egyetlen sorban tárolja: const QVAR = {...};)
    m = re.search(r"^const QVAR = (\{.*?\});$", s, re.M)
    qv = json.loads(m.group(1)) if m else None
    qadded = []
    if qv is not None:
        for v in spec["videos"]:
            pid = "v_" + v["id"]
            if v.get("qvar") and pid not in qv and f'id:"{pid}"' in s:
                qv[pid] = v["qvar"]; qadded.append(pid)
        if qadded:
            s = s[:m.start(1)] + json.dumps(qv, ensure_ascii=False, separators=(",", ":")) + s[m.end(1):]
    open(APP, "w", encoding="utf-8").write(s)
    print("beszúrva:", added, "| kérdésváltozat:", qadded)


if __name__ == "__main__":
    main()
