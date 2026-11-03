#!/usr/bin/env python3
"""0,4 mp csendet tesz a már kész videók elejére (az első kép addig áll).

Ok: görgetés után a telefon hangkimenete egy pillanatig „ébred", ezért ha a beszéd
azonnal, 0 mp-nél indul, az első szótag megakad (főleg a hangos indítású női hangoknál).
Az új videók ezt már a make_explainer.py-ból kapják; ez a régieket javítja.

Használat:  python3 tools/elocsend.py [id ...]   (id nélkül: minden AI-videó a media/ mappában)
A már javított videókat kihagyja.
"""
import os, re, subprocess, sys, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "media")
LEAD = 0.4


def lead_silence(path):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-t", "2", "-i", path, "-af",
                        "silencedetect=n=-45dB:d=0.05", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    st = re.findall(r"silence_start: ([-\d.]+)", o)
    en = re.findall(r"silence_end: ([\d.]+)", o)
    return float(en[0]) if st and float(st[0]) < 0.01 and en else 0.0


def fix(path):
    if lead_silence(path) >= LEAD - 0.05:
        print("kész volt:", os.path.basename(path)); return
    tmp = path + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", path,
                    "-vf", f"tpad=start_duration={LEAD}:start_mode=clone",
                    "-af", f"adelay={int(LEAD * 1000)}:all=1",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-profile:v", "main",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-c:a", "aac", "-b:a", "96k", tmp], check=True)
    shutil.move(tmp, path)
    print("javítva:", os.path.basename(path))


def main():
    ids = sys.argv[1:] or [os.path.basename(os.path.dirname(f))
                           for f in glob.glob(os.path.join(ROOT, "anyag", "*", "spec.json"))]
    for i in sorted(ids):
        p = os.path.join(MEDIA, i + ".mp4")
        if os.path.exists(p):
            fix(p)


if __name__ == "__main__":
    main()
