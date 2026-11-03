"""For You feed, témaszűrés, „Tudtad?” és Adataim – automata ellenőrzés egy valódi böngészőben.

A futtat.sh indítja (a helyi szerver a 8765-ös porton fut). Nem persona-szimuláció, hanem
szabályellenőrzés: hiba esetén a kilépési kód 1.
"""
import os, asyncio, sys
from playwright.async_api import async_playwright
# böngésző: alapból a gépre telepített Chrome; CI-ben CHROME_PATH="" → a Playwright saját Chromiuma
CHROME = os.environ.get("CHROME_PATH", "/usr/bin/google-chrome") or None

BASE = "http://127.0.0.1:8765/"
FUN = "Tudtad?"
FAILS, NOTES = [], []


def check(ok, msg):
    (NOTES if ok else FAILS).append(("OK   " if ok else "HIBA ") + msg)


async def current(pg):
    return await pg.evaluate("""()=>{const f=document.getElementById('feed');const its=[...f.querySelectorAll('.item')];
      const it=its[Math.round(f.scrollTop/f.clientHeight)]; if(!it) return null;
      const chip=it.querySelector('.chips span, .cchips span');
      return {kind: it.classList.contains('check') ? 'check' : it.classList.contains('end') ? 'end' : 'post',
              topic: chip ? chip.innerText.trim() : '', explore: !!it.querySelector('.chips .new'),
              title: ((it.querySelector('h3,h2')||{}).innerText||'').trim().slice(0,50)}}""")


async def walk(pg, n, dwell=250, on_post=None):
    seen = []
    for _ in range(n):
        c = await current(pg)
        if c:
            seen.append(c)
            if on_post and c["kind"] == "post":
                await on_post(c)
        await pg.wait_for_timeout(dwell)
        await pg.evaluate("()=>{const f=document.getElementById('feed');f.scrollBy({top:f.clientHeight,behavior:'instant'})}")
        await pg.wait_for_timeout(120)
    return seen


async def goto_tab(pg, hash_):
    await pg.evaluate(f"location.hash='{hash_}'")
    await pg.wait_for_timeout(500)


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=CHROME,
                                     args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"])
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="hu-HU")
        pg = await ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append((getattr(e, "stack", None) or str(e))[:400]))
        await pg.goto(BASE + "?bot=foryou")
        await pg.wait_for_timeout(1500)

        # 1) hidegindítás: legalább 3 téma kell
        go = pg.locator("#onbGo")
        check(await go.is_disabled(), "témaválasztó: 3 téma előtt a Mehet tiltva")
        for t in ["Pénzügyek", "Pszichológia"]:
            await pg.locator(f'#onb button[data-t="{t}"]').click()
        check(await go.is_disabled(), "témaválasztó: 2 témával még tiltva")
        await pg.locator(f'#onb button[data-t="{FUN}"]').click()
        check(await go.is_enabled(), "témaválasztó: 3 témával engedélyezett")
        check(await pg.locator('#onb a[href="adatvedelem.html"]').count() == 1, "témaválasztó: adatvédelmi link látszik")
        await go.click()
        await pg.wait_for_timeout(800)

        # 2) For You: a „Tudtad?” aránya és a felfedezés
        seq = await walk(pg, 60, dwell=450)
        posts = [s for s in seq if s["kind"] == "post"]
        fun = [s for s in posts if s["topic"] == FUN]
        share = len(fun) / max(1, len(posts))
        check(0.18 <= share <= 0.3, f"„Tudtad?” aránya a feedben: {share:.0%} ({len(fun)}/{len(posts)}, cél kb. 20–25%)")
        gaps, last = [], None
        for i, s in enumerate(posts):
            if s["topic"] == FUN:
                if last is not None: gaps.append(i - last)
                last = i
        if gaps:
            NOTES.append(f"INFO „Tudtad?” távolságok: {gaps}")
        expl = [s for s in posts if s["explore"]]
        NOTES.append(f"INFO „Új téma neked” címke: {len(expl)}/{len(posts)} poszton")
        dup = [posts[i]["title"] for i in range(1, len(posts)) if posts[i]["title"] == posts[i - 1]["title"]]
        check(not dup, "nincs két egymás utáni azonos poszt")

        # 3) téma kikapcsolása a Profilban
        await goto_tab(pg, "#profil")
        sw = pg.locator('#topicCtl [data-sw="Pénzügyek"]')
        check(await sw.get_attribute("aria-checked") == "true", "Profil: Pénzügyek kapcsoló bekapcsolva látszik")
        await sw.click(); await pg.wait_for_timeout(400)
        check(await sw.get_attribute("aria-checked") == "false", "Profil: Pénzügyek kikapcsolva")
        await goto_tab(pg, "#feed")
        seq = await walk(pg, 40)
        bad = [s for s in seq if s["topic"] == "Pénzügyek"]
        check(not bad, f"kikapcsolt téma nem jön elő ({len(seq)} elemből {len(bad)})")

        # 4) „Csak ezt”: csak „Tudtad?”
        await goto_tab(pg, "#profil")
        await pg.locator(f'#topicCtl [data-only="{FUN}"]').click()
        await pg.wait_for_timeout(700)
        chip = await pg.locator("#filterChip").inner_text()
        check(FUN in chip, f"„Csak ezt” mód jelzése a feed tetején: {chip.strip()!r}")
        seq = await walk(pg, 10)
        other = [s for s in seq if s["kind"] == "post" and s["topic"] != FUN]
        check(not other, f"„Csak ezt” módban csak „Tudtad?” jön ({len(other)} másik)")
        await pg.locator("#filterChip").click(); await pg.wait_for_timeout(500)
        check(await pg.locator("#filterChip").count() == 0, "a ✕ kilép a „csak ez” módból")

        # 5) mentés a Mélyebb panelből → Profil / Mentett videók
        await goto_tab(pg, "#feed")
        idx = await pg.evaluate("()=>{const f=document.getElementById('feed');return Math.round(f.scrollTop/f.clientHeight)}")
        item = pg.locator("#feed .item").nth(idx)
        if await item.locator("button.deeper").count():
            await item.locator("button.deeper").click(); await pg.wait_for_timeout(400)
            await pg.locator("#sheetSave").click(); await pg.wait_for_timeout(300)
            check(await pg.locator("#sheetSave").get_attribute("aria-pressed") == "true", "Mélyebb panel: Mentés gomb működik")
            await pg.keyboard.press("Escape")
            await goto_tab(pg, "#profil")
            check(await pg.locator("#savedCard").is_visible(), "Profil: Mentett videók kártya megjelent")
        else:
            FAILS.append("HIBA az aktuális elem nem poszt, a mentést nem lehetett kipróbálni")

        # 6) érdeklődési profil, kikapcsolás, törlés
        await goto_tab(pg, "#profil")
        bars = await pg.locator("#ibars .ibar").count()
        check(bars >= 3, f"Profil: érdeklődési sávok ({bars} téma)")
        note = await pg.locator("#profNote").inner_text()
        check("videónál mért" in note, f"Profil: a mért jelek száma látszik ({note[:60]!r})")
        await pg.locator("#dProf").click(); await pg.locator("#dYes").click(); await pg.wait_for_timeout(400)
        note = await pg.locator("#profNote").inner_text()
        check("Még nincs elég jel" in note, "Érdeklődési profil törlése után nincs mért jel")
        await pg.locator("#trackSw").click(); await pg.wait_for_timeout(300)
        check(await pg.locator("#trackSw").get_attribute("aria-checked") == "false", "személyre szabás kikapcsolható")
        await goto_tab(pg, "#feed"); await walk(pg, 6); await goto_tab(pg, "#profil")
        note = await pg.locator("#profNote").inner_text()
        check("ki van kapcsolva" in note, "kikapcsolt mérésnél nem gyűlik jel")
        await pg.locator("#trackSw").click()

        # 7) letöltés és „minden adat törlése” (a teszt-backendben nincs account → e-mailes útmutató)
        await pg.locator("#dExport").click(); await pg.wait_for_timeout(300)
        check("Letöltve" in await pg.locator("#toast").inner_text(), "Adataim letöltése: a letöltés elindul")
        await pg.locator("#dAll").click(); await pg.wait_for_timeout(200)
        txt = await pg.locator("#dataBox").inner_text()
        check("neumann.peter1231@gmail.com" in txt or "Biztosan" in txt, "Minden adatom törlése: megerősítés vagy útmutató")

        # 7b) adatcsökkentés: adattakarékos kapcsoló, verziózott és kicsinyített média
        lsw = pg.locator("#liteSw")
        was = await lsw.get_attribute("aria-checked")
        await lsw.click(); await pg.wait_for_timeout(200)
        check(await lsw.get_attribute("aria-checked") != was, "Adattakarékos mód kapcsolható")
        check("nem töltjük le előre" in await pg.locator("#liteNote").inner_text() or was == "true", "Adattakarékos mód: magyarázat látszik")
        await lsw.click()
        media = await pg.evaluate("""async()=>{const t=await (await fetch('/app.js')).text();
            const m=[...t.matchAll(/media\\/[A-Za-z0-9_./-]+?\\.(mp4|webp|jpg)(\\?v=[0-9a-f]{8})?/g)];
            return {n:m.length, ver:m.filter(x=>x[2]).length, jpg:m.filter(x=>x[1]==='jpg').length}}""")
        check(media["n"] > 0 and media["ver"] == media["n"], f"minden médialink verziózott ({media['ver']}/{media['n']})")
        check(media["jpg"] == 0, f"a poszterek WebP-ben ({media['jpg']} JPG maradt)")
        sizes = await pg.evaluate("""async()=>{const t=await (await fetch('/app.js')).text();
            const u=[...new Set([...t.matchAll(/media\\/[A-Za-z0-9_./-]+?\\.mp4\\?v=[0-9a-f]{8}/g)].map(x=>x[0]))];
            let s=0; for (const x of u) { const r=await fetch('/'+x,{method:'HEAD'}); s+=+r.headers.get('content-length')||0; }
            return {n:u.length, avg:Math.round(s/Math.max(1,u.length)/1024)}}""")
        check(sizes["avg"] < 2600, f"videók átlagmérete {sizes['avg']} KB ({sizes['n']} videó, cél < 2,6 MB)")

        # 8) személyre szabás hatása: új böngésző, csak Pénzügyek-et lájkol, a többit átlapozza
        ctx2 = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="hu-HU")
        p2 = await ctx2.new_page()
        p2.on("pageerror", lambda e: errs.append((getattr(e, "stack", None) or str(e))[:400]))
        await p2.goto(BASE + "?bot=szemely"); await p2.wait_for_timeout(1200)
        await p2.locator("#onbAll").click(); await p2.wait_for_timeout(600)

        async def like_money(c):
            if c["topic"] == "Pénzügyek":
                i = await p2.evaluate("()=>{const f=document.getElementById('feed');return Math.round(f.scrollTop/f.clientHeight)}")
                await p2.locator("#feed .item").nth(i).locator('button[data-a="like"]').click()
                await p2.wait_for_timeout(3200)   # végignézés helyett: hosszabb nézés + lájk
        first = await walk(p2, 30, dwell=500, on_post=like_money)
        await goto_tab(p2, "#profil"); await goto_tab(p2, "#feed")   # új feed a frissült profillal
        later = await walk(p2, 30, dwell=300)
        sh = lambda l: sum(1 for s in l if s["topic"] == "Pénzügyek") / max(1, sum(1 for s in l if s["kind"] == "post"))
        NOTES.append(f"INFO Pénzügyek aránya: első 30 elem {sh(first):.0%}, a lájkok után {sh(later):.0%}")
        await goto_tab(p2, "#profil")
        top = await p2.locator("#ibars .ibar span").first.inner_text()
        check(top == "Pénzügyek", f"a lájkolt téma lett az érdeklődési profil élén ({top})")

        check(not errs, "nincs JS-hiba" + ("" if not errs else ": " + " | ".join(errs[:3])))
        await b.close()
    print("\n".join(NOTES + FAILS))
    print(f"\n{len(FAILS)} hiba")
    sys.exit(1 if FAILS else 0)


asyncio.run(main())
