#!/usr/bin/env python3
"""Gyártósor egy lépésben (2026-11-03): forgatókönyvből kész, appba beírt videó – helyben és a felhőben
(.github/workflows/gyartas.yml) is ugyanígy fut.

Használat:
  python3 tools/gyartas.py anyag/funfact1.json                 # minden még kész videó nélküli tétel
  python3 tools/gyartas.py anyag/sorozat5.json csalo1 csalo2   # csak a megadott id-k
  Kapcsolók: --becsles  csak a költségbecslés, semmi nem fut
             --proba    API nélkül, helyettesítő képpel és hanggal (ingyenes próba, élesbe nem való)
             --max-kep N  legfeljebb ennyi képet generálhat (költségfék, alapból 30)
             --kimenet F  az összefoglaló Markdown-fájl (a PR leírása), alapból gyartas_osszefoglalo.md

Lépések: ellenoriz.py → (hang.py + kepek.py | proba_anyag.py) → osszerak.py (+kisebb.py) →
funfact.py / posztok.py → kontaktlap → build.py → ellenoriz.py újra.
Csak azokat a videókat gyártja, amelyekhez még nincs media/<id>.mp4 (a képek és hangok nincsenek a gitben,
ezért egy kész videó újragyártása fölöslegesen újra kifizetné a képeket).
"""
import argparse, glob, json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEP_AR = 0.067            # $/kép (Gemini Nano Banana 2.1, MUNKAFUZET)
TTS_AR = 0.03             # $/videó, Gemini TTS (becslés: „pár cent videónként”)
GEMINI_HANGOK = {"gemini_charon", "gemini_orus", "gemini_fenrir", "gemini_kore", "gemini_aoede"}
ELEVEN_HANGOK = {"gabor", "vera_tanito", "vera_kozepes", "vera_elenk"}


def run(*cmd):
    print("▶", " ".join(cmd[1:] if cmd[0] == sys.executable else cmd), flush=True)
    subprocess.run(list(cmd), check=True, cwd=ROOT)


def py(script, *args):
    run(sys.executable, os.path.join(ROOT, "tools", script), *args)


def secrets():
    env, p = {}, os.path.join(ROOT, ".secrets.env")
    if os.path.exists(p):
        for line in open(p):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                if v:
                    env[k] = v
    return env


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout)
    except ValueError:
        return 0.0


def kontaktlap(v):
    """A jelenetképek egy lapon, a jelenet szövegével – ezen nézi át Péter, nincs-e szöveg, valódi személy, márka."""
    d = os.path.join(ROOT, "anyag", v["id"])
    imgs = [os.path.join(d, f"{i + 1:02d}.png") for i in range(len(v["scenes"]))]
    imgs = [p for p in imgs if os.path.exists(p)]
    if not imgs:
        return None
    tw, th, cap, cols = 270, 480, 64, 3
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 10, rows * (th + cap) + (rows + 1) * 10), (14, 17, 22))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for k, p in enumerate(imgs):
        x, y = 10 + (k % cols) * (tw + 10), 10 + (k // cols) * (th + cap + 10)
        im = Image.open(p).convert("RGB")
        im.thumbnail((tw, th))
        sheet.paste(im, (x, y))
        words, line, lines = v["scenes"][k]["text"].split(), "", []
        for w in words:
            if len(line) + len(w) > 34:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        dr.text((x, y + th + 4), f"{k + 1}. " + "\n".join(lines[:3]), fill=(230, 230, 230), font=font)
    out_dir = os.path.join(ROOT, "anyag", "kontaktlap")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, v["id"] + ".jpg")
    sheet.save(out, quality=80)
    return os.path.relpath(out, ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("forgatokonyv")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--becsles", action="store_true")
    ap.add_argument("--proba", action="store_true")
    ap.add_argument("--max-kep", type=int, default=30)
    ap.add_argument("--kimenet", default="gyartas_osszefoglalo.md")
    a = ap.parse_args()

    path = os.path.relpath(os.path.abspath(a.forgatokonyv), ROOT)
    spec = json.load(open(os.path.join(ROOT, path), encoding="utf-8"))
    fun = os.path.basename(path).startswith("funfact")
    videos = [v for v in spec["videos"] if not a.ids or v["id"] in a.ids]
    if a.ids and len(videos) != len(set(a.ids)):
        sys.exit(f"Ismeretlen id: {sorted(set(a.ids) - {v['id'] for v in videos})}")
    todo = [v for v in videos if not os.path.exists(os.path.join(ROOT, "media", v["id"] + ".mp4"))]
    kesz = [v["id"] for v in videos if v not in todo]

    # költségbecslés és fékek
    kepek = sum(len(v["scenes"]) for v in todo)
    eleven = [v for v in todo if v.get("hang") in ELEVEN_HANGOK]
    eleven_kar = sum(len(s["text"]) for v in eleven for s in v["scenes"])
    koltseg = 0 if a.proba else kepek * KEP_AR + TTS_AR * (len(todo) - len(eleven))
    print(f"Forgatókönyv: {path} · gyártandó: {len(todo)} videó ({', '.join(v['id'] for v in todo) or '–'})"
          + (f" · már kész, kihagyva: {', '.join(kesz)}" if kesz else ""))
    print(f"Becslés: {kepek} kép, ElevenLabs {eleven_kar} karakter, kb. {koltseg:.2f} $" + (" (PRÓBA: 0 $)" if a.proba else ""))
    hiba = []
    if not todo:
        hiba.append("Nincs gyártandó videó: mindegyikhez van már media/<id>.mp4.")
    if kepek > a.max_kep and not a.proba:
        hiba.append(f"{kepek} kép kellene, a keret {a.max_kep} (--max-kep). Adj meg kevesebb id-t, vagy emeld a keretet.")
    nincs_hang = [v["id"] for v in todo if v.get("hang") not in GEMINI_HANGOK | ELEVEN_HANGOK]
    if nincs_hang:
        hiba.append(f"Nincs (vagy ismeretlen) „hang” mező: {', '.join(nincs_hang)} – a hang.py különben véletlenül ElevenLabs-hangot választana.")
    env = secrets()
    if not a.proba and not a.becsles:
        if "GEMINI_API_KEY" not in env:
            hiba.append("Hiányzik a GEMINI_API_KEY (.secrets.env, a felhőben a GitHub Secrets).")
        if eleven and "ELEVENLABS_API_KEY" not in env:
            hiba.append(f"ElevenLabs-hangot kér: {', '.join(v['id'] for v in eleven)}, de hiányzik az ELEVENLABS_API_KEY.")
    if hiba:
        print("\n".join("HIBA " + h for h in hiba))
        sys.exit(2)
    if a.becsles:
        return

    ids = [v["id"] for v in todo]
    py("ellenoriz.py", path)
    if a.proba:
        py("proba_anyag.py", path, *ids)
    else:
        py("hang.py", path, *ids)
        py("kepek.py", path, *ids)
    py("osszerak.py", path, *ids)
    hianyzik = [i for i in ids if not os.path.exists(os.path.join(ROOT, "media", i + ".mp4"))]
    if hianyzik:
        sys.exit(f"HIBA: nem készült el a videó: {', '.join(hianyzik)}")
    if fun:
        py("funfact.py", *sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "anyag", "funfact*.json"))))
    else:
        py("posztok.py", path)
    lapok = {v["id"]: kontaktlap(v) for v in todo}
    run(sys.executable, os.path.join(ROOT, "build.py"))
    py("ellenoriz.py")

    # összefoglaló a PR-hoz
    sor = []
    for v in todo:
        mp4 = os.path.join(ROOT, "media", v["id"] + ".mp4")
        sor.append(f"| {v['title']} (`{v['id']}`) | {duration(mp4):.0f} mp | {os.path.getsize(mp4) // 1024} KB | "
                   f"{v.get('hang')} | {len(v['scenes'])} | {('`' + lapok[v['id']] + '`') if lapok[v['id']] else '–'} |")
    md = [("> ⚠️ **PRÓBA** – helyettesítő képek és sípszó-hang, API nélkül. **Ne olvaszd be élesbe**, csak a gyártósort ellenőrzi.\n"
           if a.proba else ""),
          f"Forgatókönyv: `{path}` · {len(todo)} új videó · becsült költség: **{koltseg:.2f} $**"
          + (f" (ElevenLabs: {eleven_kar} karakter)" if eleven_kar else ""), "",
          "| Videó | Hossz | Méret | Hang | Jelenet | Kontaktlap |", "|---|---|---|---|---|---|", *sor, "",
          "**Átnézendő beolvasztás előtt** (a kontaktlapokon és a videóban):",
          "- nincs szöveg, felirat, szám vagy logó a képeken; nincs felismerhető valódi személy, márka, ismert rajzfilmfigura;",
          "- a hang érthető, az első szótag nem akad meg (0,4 mp csend az elején);",
          "- a „Mélyebben” rész és a forrás stimmel."]
    open(os.path.join(ROOT, a.kimenet), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"Kész: {', '.join(ids)} · összefoglaló: {a.kimenet}")


if __name__ == "__main__":
    main()
