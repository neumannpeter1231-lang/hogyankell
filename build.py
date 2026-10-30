#!/usr/bin/env python3
"""Hogyankell webapp összerakása a prototípusból.

Használat:  python3 build.py
A kimenet a site/ mappa; a Cloudflare ezt teszi ki a main ág minden frissítésekor.
"""
import json, os, shutil, sys, time
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "prototipus", "hogyankell.html")
MEDIA = os.path.join(ROOT, "media")
SITE = os.path.join(ROOT, "site")
SRC = os.path.join(ROOT, "webapp")
SUPABASE_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.3/dist/umd/supabase.js"

GATE_CSS = """
/* zárt webapp: belépőkapu, kezdőképernyős mód */
body.locked .app{display:none}
.gate{position:fixed;inset:0;z-index:100;background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:24px;text-align:center}
.gate h1{font-size:32px}
.gate p{margin:0;max-width:32ch;color:#D5DAE1}
.gate .g-muted{color:var(--muted);font-size:14px}
.gate .g-err{color:var(--bad);font-size:14px}
.g-logo{width:84px;height:84px;border-radius:24px;background:var(--yel);color:var(--yel-ink);display:flex;align-items:center;justify-content:center;margin-bottom:6px}
.g-btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;border:0;border-radius:12px;min-height:50px;padding:0 20px;font-weight:700;font-size:16px;background:#fff;color:#1f1f1f;cursor:pointer}
.g-btn.alt{background:var(--surface-2);color:var(--ink)}
.g-row{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
/* telefonon a teljes képernyőt kitöltse (iPhone kezdőképernyős módban is) */
html,body{height:100%;overflow:hidden;overscroll-behavior:none}
.app{position:fixed;top:0;bottom:0;left:0;right:0;height:auto;margin:0 auto}
@supports (padding:env(safe-area-inset-bottom)){
  .nav{height:calc(64px + env(safe-area-inset-bottom));padding-bottom:env(safe-area-inset-bottom)}
  .feed-top{padding-top:calc(14px + env(safe-area-inset-top))}
  .chips{top:calc(58px + env(safe-area-inset-top))}
  .scroll{padding-top:calc(20px + env(safe-area-inset-top))}
  .check{padding-top:calc(70px + env(safe-area-inset-top))}
  .toast{top:calc(64px + env(safe-area-inset-top))}
  .duel-play,.onb{padding-top:calc(18px + env(safe-area-inset-top))}
  .gate{padding-top:calc(24px + env(safe-area-inset-top));padding-bottom:calc(24px + env(safe-area-inset-bottom))}
}
"""


def split_app(src):
    i_app = src.index('<div class="app" id="app">')
    i_s = src.index("<script>", i_app)
    i_e = src.rindex("</script>")
    head = src[:i_app]
    markup = src[i_app:i_s]
    script = src[i_s + len("<script>"):i_e]
    title_end = head.index("</title>") + len("</title>")
    head_rest = head[title_end:]
    return head_rest, markup, script


def icons(dst):
    os.makedirs(dst, exist_ok=True)
    YEL, INK = (242, 194, 48), (20, 18, 10)

    def draw(size, pad_ratio, bg_round=True, mono=False):
        S = size * 4
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if mono:
            fg = (255, 255, 255, 255)
        else:
            if bg_round:
                d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=YEL)
            else:
                d.rectangle([0, 0, S, S], fill=YEL)
            fg = INK
        pad = S * pad_ratio
        w = S - 2 * pad
        def P(x, y):
            return (pad + x / 24 * w, pad + y / 24 * w)
        lw = int(w / 24 * 2.3)
        def poly(pts, closed=False):
            pts = [P(*p) for p in pts]
            if closed:
                pts = pts + [pts[0]]
            d.line(pts, fill=fg, width=lw, joint="curve")
            for q in pts:
                d.ellipse([q[0] - lw / 2, q[1] - lw / 2, q[0] + lw / 2, q[1] + lw / 2], fill=fg)
        poly([(12, 2), (22, 7), (12, 12), (2, 7)], closed=True)
        poly([(2, 17), (12, 22), (22, 17)])
        poly([(2, 12), (12, 17), (22, 12)])
        return im.resize((size, size), Image.LANCZOS)

    draw(192, 0.2).save(os.path.join(dst, "icon-192.png"))
    draw(512, 0.2).save(os.path.join(dst, "icon-512.png"))
    draw(512, 0.28, bg_round=False).save(os.path.join(dst, "icon-maskable-512.png"))
    draw(180, 0.2, bg_round=False).convert("RGB").save(os.path.join(dst, "apple-touch-icon.png"))
    draw(96, 0.12, mono=True).save(os.path.join(dst, "badge-96.png"))
    draw(48, 0.2).save(os.path.join(dst, "favicon-48.png"))


def main():
    keys = json.load(open(os.path.join(SRC, "build-config.json")))
    url = sys.argv[1] if len(sys.argv) > 1 else keys["supabaseUrl"]
    key = sys.argv[2] if len(sys.argv) > 2 else keys["supabaseKey"]
    version = time.strftime("%Y%m%d%H%M")

    if os.path.exists(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    head_rest, markup, script = split_app(open(APP, encoding="utf-8").read())
    style_end = head_rest.rindex("</style>")
    head_rest = head_rest[:style_end] + GATE_CSS + head_rest[style_end:]

    index = f"""<!doctype html>
<html lang="hu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#0E1116">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Hogyankell">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icons/favicon-48.png" sizes="48x48">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<title>Hogyankell</title>{head_rest}</head>
<body class="locked">
{markup}
<div id="gate" class="gate"><p class="g-muted">Betöltés…</p></div>
<script src="/config.js?v={version}"></script>
<script src="{SUPABASE_JS}"></script>
<script src="/backend.js?v={version}"></script>
</body>
</html>
"""
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(index)
    open(os.path.join(SITE, "app.js"), "w", encoding="utf-8").write(script.strip() + "\n")
    cfg = open(os.path.join(SRC, "config.template.js"), encoding="utf-8").read()
    cfg = cfg.replace("__SUPABASE_URL__", url.rstrip("/")).replace("__SUPABASE_KEY__", key) \
             .replace("__VAPID_PUBLIC__", keys["vapidPublicKey"]).replace("__VERSION__", version)
    open(os.path.join(SITE, "config.js"), "w", encoding="utf-8").write(cfg)
    for f in ["backend.js", "sw.js", "manifest.webmanifest", "_headers", "adatvedelem.html"]:
        shutil.copy(os.path.join(SRC, f), os.path.join(SITE, f))
    shutil.copytree(MEDIA, os.path.join(SITE, "media"))
    icons(os.path.join(SITE, "icons"))
    print("site/ kész, verzió:", version)


if __name__ == "__main__":
    main()
