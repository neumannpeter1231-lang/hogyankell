#!/usr/bin/env python3
"""Adatcsökkentés: a videók 540×960-ra, 280 kbit/s-ra (kétmenetes H.264), a hang mono 64 kbit/s-ra,
a poszterképek 540 széles WebP-re (2026-11-03, Péter döntése: 540p).

Használat:
  python3 tools/kisebb.py                 # minden media/*.mp4 és media/clips/*.mp4 + poszterek
  python3 tools/kisebb.py media/citrom.mp4 # csak a megadott videók (+ a posztereik)

A már 540 széles videókat kihagyja, így bármikor újrafuttatható. Az osszerak.py a kész videóra magától lefuttatja.
"""
import glob, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, VBR, VMAX, ABR = 540, 960, "280k", "350k", "64k"


def width(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                        "-of", "json", path], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)["streams"][0]["width"]
    except Exception:
        return 0


def video(path):
    if width(path) <= W:
        return "kihagyva (már kicsi)"
    before = os.path.getsize(path)
    with tempfile.TemporaryDirectory() as tmp:
        out, log = os.path.join(tmp, "out.mp4"), os.path.join(tmp, "pass")
        v = ["-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-profile:v", "main",
             "-b:v", VBR, "-maxrate", VMAX, "-bufsize", "700k", "-pix_fmt", "yuv420p", "-passlogfile", log]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, *v, "-pass", "1", "-an", "-f", "mp4", os.devnull],
                       check=True, cwd=tmp)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, *v, "-pass", "2",
                        "-c:a", "aac", "-b:a", ABR, "-ac", "1", "-movflags", "+faststart", out], check=True, cwd=tmp)
        os.replace(out, path)
    return f"{before // 1024} KB → {os.path.getsize(path) // 1024} KB"


def poster(jpg):
    webp = jpg[:-4] + ".webp"
    if os.path.exists(webp) and os.path.getmtime(webp) >= os.path.getmtime(jpg):
        return None
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", jpg, "-vf", f"scale={W}:-2:flags=lanczos",
                    "-c:v", "libwebp", "-quality", "72", webp], check=True)
    return f"{os.path.getsize(jpg) // 1024} KB → {os.path.getsize(webp) // 1024} KB"


def main():
    vids = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "media", "*.mp4")) + glob.glob(os.path.join(ROOT, "media", "clips", "*.mp4")))
    for v in vids:
        print(os.path.relpath(v, ROOT), video(v), flush=True)
        jpg = v[:-4] + ".jpg"
        if os.path.exists(jpg):
            r = poster(jpg)
            if r:
                print("  poszter", r, flush=True)


if __name__ == "__main__":
    main()
