#!/usr/bin/env python3
"""Forgatókönyv-ellenőrző (2026-11-03): a tartalmi szabályok gépi ellenőrzése, a CI is ezt futtatja.

Használat: python3 tools/ellenoriz.py [anyag/sorozatN.json ...]   (fájl nélkül: minden anyag/sorozat*.json és funfact*.json)

HIBA (kilépési kód 1), ha:
  - egy cím vagy id már létezik (másik posztnál, a meglévő appban is) – a téma nem ismétlődhet
  - hiányzik a forrás, a szavazás, az ellenőrző kérdés vagy a Mélyebben rész, vagy hibás a helyes válasz indexe
  - nincs 2 kérdésváltozat (sem a JSON-ban, sem az app QVAR-jában)
  - „Tudtad?” fun factnél hiányzik a tanulság, vagy az utolsó jelenet nem „A tanulság:”-tal kezdődik
  - sorozatvideónál hiányzik a szokás (habit) – a posztok.py enélkül nem tudja beírni
FIGYELMEZTETÉS (nem állítja meg a CI-t), ha:
  - nem stimmel a jelenetszám (sorozat 6, fun fact 4) vagy a becsült hossz (sorozat 25–35 mp, fun fact 15–30 mp)
  - sorozatvideó utolsó jelenete nem „A tipp:”
  - egy fájlon belül két egymást követő videónak ugyanaz a hangja

A 2026-11-01 előtti sorozatok (sorozat1–3) a kérdésváltozat és a jelenetszám szabálya alól „régi” kivételt kapnak
(figyelmeztetés hiba helyett), mert akkor ezek a szabályok még nem léteztek.
"""
import glob, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "prototipus", "hogyankell.html")
REGI = {"sorozat1.json", "sorozat2.json", "sorozat3.json"}
KAR_PER_MP = 14.5          # mérve 22 kész videón: 13,8–15,8 karakter/mp, a becslés ±3 mp
FUN = "Tudtad?"


def norm(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def app_posts():
    """A meglévő app posztjai: {id: cím}, a rejtett (HIDE) duplikátumok nélkül, és a QVAR kulcsai."""
    s = open(APP, encoding="utf-8").read()
    hide = set(json.loads((re.search(r"^const HIDE = (\[[^\]]*\])", s, re.M) or [None, "[]"])[1]))
    posts = {}
    for m in re.finditer(r'"?id"?\s*:\s*"([^"]+)"(?:(?!"?id"?\s*:\s*").){0,600}?"?title"?\s*:\s*"([^"]+)"', s, re.S):
        if m.group(1) not in hide:
            posts.setdefault(m.group(1), m.group(2))
    q = re.search(r"^const QVAR = (\{.*?\});$", s, re.M)
    qvar = set(json.loads(q.group(1))) if q else set()
    fq = re.search(r"^const FUN_QVAR = (\{.*?\});$", s, re.M)
    if fq:
        qvar |= set(json.loads(fq.group(1)))
    return posts, qvar


def qblock(v, key, errs, label):
    b = v.get(key)
    if not isinstance(b, dict) or not str(b.get("q", "")).strip():
        errs.append(f"{label}: hiányzik a(z) {key} kérdés"); return
    o = b.get("o") or []
    if len(o) < 2:
        errs.append(f"{label}: a(z) {key} kérdésnek legalább 2 válasza kell")
    if not isinstance(b.get("a"), int) or not 0 <= b["a"] < len(o):
        errs.append(f"{label}: a(z) {key} helyes válaszának indexe ({b.get('a')}) nincs a válaszok között")
    if not str(b.get("why", "")).strip():
        errs.append(f"{label}: a(z) {key} kérdéshez nincs magyarázat (why)")


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "anyag", "sorozat*.json")) +
                                   glob.glob(os.path.join(ROOT, "anyag", "funfact*.json")))
    posts, qvar = app_posts()
    errs, warns, seen = [], [], {}
    # a meglévő app-posztok címei: a forgatókönyvből beírt poszt saját magával nem ütközik
    by_title = {}
    for pid, t in posts.items():
        by_title.setdefault(norm(t), set()).add(pid)
    n = 0
    for f in files:
        base = os.path.basename(f)
        regi = base in REGI
        spec = json.load(open(f, encoding="utf-8"))
        prev_hang = None
        for v in spec.get("videos", []):
            n += 1
            fun = base.startswith("funfact") or v.get("topic") == FUN
            pid = ("f_" if fun else "v_") + v["id"]
            label = f"{base} / {v['id']}"
            # 1) ismétlődés: id és cím
            if v["id"] in seen:
                errs.append(f"{label}: az id már szerepel itt is: {seen[v['id']]}")
            seen[v["id"]] = label
            nt = norm(v.get("title", ""))
            if not nt:
                errs.append(f"{label}: nincs cím")
            for t, ids in by_title.items():
                same = t == nt or (min(len(t), len(nt)) >= 6 and (t.startswith(nt) or nt.startswith(t)))
                other = ids - {pid}
                if same and other:
                    errs.append(f"{label}: a „{v.get('title')}” cím (vagy nagyon hasonló) már létezik: {', '.join(sorted(other))}")
            by_title.setdefault(nt, set()).add(pid)
            # 2) kötelező részek
            src = v.get("source") or {}
            if not str(src.get("label", "")).strip():
                errs.append(f"{label}: nincs forrás (source.label)")
            if not v.get("deeper"):
                errs.append(f"{label}: nincs Mélyebben rész (deeper)")
            qblock(v, "poll", errs, label)
            qblock(v, "check", errs, label)
            qv = v.get("qvar") or []
            for i, b in enumerate(qv):
                qblock({"x": b}, "x", errs, f"{label} (qvar {i + 1})")
            if len(qv) < 2 and pid not in qvar:
                (warns if regi else errs).append(f"{label}: nincs 2 kérdésváltozat (qvar) – {'régi sorozat' if regi else 'új videónál kötelező'}")
            scenes = v.get("scenes") or []
            last = (scenes[-1].get("text", "") if scenes else "").strip()
            if fun:
                if not str(v.get("lesson", "")).strip():
                    errs.append(f"{label}: a fun factnél nincs egy mondatos tanulság (lesson)")
                if not last.startswith("A tanulság:"):
                    errs.append(f"{label}: az utolsó jelenet nem „A tanulság:”-tal kezdődik")
            else:
                if not v.get("habit"):
                    errs.append(f"{label}: nincs szokás (habit) – a posztok.py enélkül nem tudja beírni")
                if not last.startswith("A tipp:"):
                    warns.append(f"{label}: az utolsó jelenet nem „A tipp:”-pel kezdődik")
            # 3) forma
            want = 4 if fun else 6
            if len(scenes) != want:
                warns.append(f"{label}: {len(scenes)} jelenet (a szabály szerint {want})")
            sec = sum(len(s.get("text", "")) for s in scenes) / KAR_PER_MP
            lo, hi = (15, 30) if fun else (25, 35)
            if not lo <= sec <= hi:
                warns.append(f"{label}: becsült hossz kb. {sec:.0f} mp (cél {lo}–{hi} mp)")
            h = v.get("hang")
            if h and h == prev_hang:
                warns.append(f"{label}: ugyanaz a hang ({h}), mint az előző videóé – két egymást követőben ne legyen ugyanaz")
            prev_hang = h or prev_hang
    print(f"Ellenőrizve: {n} videó, {len(files)} fájl")
    for w in warns:
        print("FIGYELEM", w)
    for e in errs:
        print("HIBA    ", e)
    print(f"\n{len(errs)} hiba, {len(warns)} figyelmeztetés")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
