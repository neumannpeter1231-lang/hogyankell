"""5 véletlenszerűen sorsolt AI-tesztelő (a 26 fős panelből) végigkattintja az appot egy valódi böngészőben.
Szimuláció: a viselkedést a persona leírásából becsült valószínűségek vezérlik, nem valódi emberek."""
import asyncio, json, random, sys, time
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8765/"
# név: (leírás, türelem mp/poszt, like, dislike, komment, mélyebb, szavazás, helyes válasz esélye, szokás, témák, komment-szöveg)
PANEL = {
 "Lili": ("19, egyetemista, sokat TikTokozik", (2,5), .6, .15, .25, .1, .5, .6, .1, None, "ez nagyon ott van, a csalimadaras meglepett"),
 "Bence": ("24, junior értékesítő", (4,8), .5, .1, .2, .4, .7, .75, .3, ["Meggyőzés","Kommunikáció"], "ezt holnap kipróbálom egy ügyfélnél"),
 "Kata": ("31, kisgyerekes anyuka", (3,6), .4, .1, .15, .2, .5, .7, .4, ["Pénzügyek","Alvás és egészség"], "rövid és érthető, ez kell nekem"),
 "Tamás": ("45, kisvállalkozó, szkeptikus", (5,10), .2, .3, .3, .7, .6, .8, .1, ["Pénzügyek","Meggyőzés"], "honnan van ez a szám? a forrás jó, hogy ott van"),
 "Dóri": ("22, pszichológia szakos", (5,10), .6, .05, .3, .8, .8, .9, .3, ["Pszichológia","Meggyőzés"], "a mélyebben részben jó, hogy a korlátokat is leírjátok"),
 "Máté": ("20, gamer", (2,4), .4, .2, .1, .05, .8, .5, .05, None, "a pontok jók, aréna mikor lesz izgibb?"),
 "Erzsi": ("67, nyugdíjas", (6,10), .3, .1, .1, .2, .4, .6, .3, ["Pénzügyek","Biztonság otthon"], "kicsit gyors nekem, de szép a rajz"),
 "Gergő": ("38, középiskolai tanár", (5,9), .5, .05, .2, .7, .7, .85, .2, None, "ezt az órán is levetíteném"),
 "Nóra": ("29, ápoló", (3,6), .4, .1, .1, .3, .5, .7, .3, ["Alvás és egészség","Pszichológia"], "a hideg vizes példa jobb, mint a kórházas"),
 "Zoli": ("41, kamionsofőr", (3,7), .3, .2, .05, .1, .4, .6, .1, ["Pénzügyek","Biztonság otthon"], "hang nélkül nem nagyon tudom nézni vezetés közben"),
 "Bianka": ("34, HR-es", (4,8), .5, .1, .2, .5, .6, .8, .3, ["Kommunikáció","Pszichológia"], "a holdudvarhatást minden interjúztatónak látnia kéne"),
 "Dávid": ("27, programozó", (3,6), .4, .15, .1, .6, .7, .85, .1, None, "betöltés gyors, egy-két gomb kicsi"),
 "Réka": ("20, egyetemista", (2,5), .6, .1, .2, .2, .6, .65, .2, None, "imádom a rajzstílust"),
 "Ádám": ("36, kétgyerekes apa", (3,7), .4, .1, .1, .3, .5, .7, .4, ["Pénzügyek","Idő és fókusz"], "az elsüllyedt költség pont rólam szól"),
 "Fanni": ("26, fodrász", (2,5), .6, .1, .2, .1, .5, .6, .2, ["Kommunikáció","Meggyőzés"], "a vendégeimnek is elmondom"),
 "Krisztián": ("30, startupalapító", (3,6), .5, .1, .2, .5, .7, .8, .2, ["Meggyőzés","Pénzügyek"], "a csalimadarat mi is használjuk az árazásnál"),
 "Petra": ("28, ingatlanos", (3,7), .5, .1, .2, .4, .6, .75, .2, ["Meggyőzés","Kommunikáció"], "a keretezés napi munkám része"),
 "Bálint": ("21, közgáz hallgató", (3,7), .5, .1, .2, .6, .8, .85, .1, ["Pénzügyek","Pszichológia"], "kahneman! a veszteségkerülést tanultuk"),
 "Lara": ("23, influenszer", (2,4), .7, .1, .3, .1, .5, .6, .1, None, "ezt reelsbe is megosztanám"),
 "Feri": ("50, biztonsági őr", (4,8), .3, .2, .05, .1, .4, .6, .1, ["Biztonság otthon","Pénzügyek"], "a csalásokról jöhetne több"),
 "Judit": ("44, könyvelő", (5,9), .4, .1, .1, .6, .7, .85, .3, ["Pénzügyek"], "a számok stimmelnek, ellenőriztem"),
 "Márk": ("25, edző", (2,5), .5, .1, .1, .2, .6, .6, .5, ["Alvás és egészség","Idő és fókusz"], "a szokás rész jó ötlet"),
 "dr. Kovács Anna": ("40, pszichológus", (6,10), .4, .05, .3, .9, .8, .9, .2, ["Pszichológia"], "korrekt, de a holdudvarnál árnyalnám a kutatást"),
 "Tibi": ("33, gyári műszakos", (2,5), .4, .2, .05, .05, .4, .55, .1, None, "jó hogy egyszerűen beszél"),
 "Dorina": ("22, pincér", (2,5), .5, .1, .15, .1, .5, .6, .2, ["Kommunikáció","Pszichológia"], "a csúcs-vég szabályt a vendégeknél is látom"),
 "Ilona": ("60, nagymama", (6,10), .3, .1, .1, .1, .3, .5, .3, ["Pénzügyek","Alvás és egészség"], "nagyobb betű kellene"),
}


async def bot(pw, name, posts_to_watch, outdir):
    desc, (tmin, tmax), pl, pd, pc, pdeep, ppoll, pacc, phab, topics, ctext = PANEL[name]
    r = random.Random()
    log = {"name": name, "desc": desc, "errors": [], "seen": [], "actions": [], "video_issues": [], "layout": []}
    b = await pw.chromium.launch(executable_path="/usr/bin/google-chrome",
                                 args=["--autoplay-policy=no-user-gesture-required", "--mute-audio"])
    ctx = await b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2,
                              locale="hu-HU")
    pg = await ctx.new_page()
    pg.on("pageerror", lambda e: log["errors"].append("JS: " + str(e)[:200]))
    pg.on("console", lambda m: m.type == "error" and log["errors"].append("console: " + m.text[:200]))
    pg.on("requestfailed", lambda q: log["errors"].append("kérés: " + q.url[-60:] + " " + (q.failure or "")))
    t0 = time.time()
    await pg.goto(BASE + "?bot=" + name.split()[-1])
    await pg.wait_for_timeout(1500)
    # 1) témaválasztó
    if topics:
        for tp in topics:
            btn = pg.locator(f'button[data-t="{tp}"]')
            if await btn.count(): await btn.first.click()
        go = pg.locator("#onbGo")
        await go.click()
        log["actions"].append("témák: " + ", ".join(topics))
    else:
        await pg.locator("#onbAll").click()
        log["actions"].append("témák: mindegy")
    await pg.wait_for_timeout(1200)
    await pg.screenshot(path=f"{outdir}/{name.split()[-1]}_1_feed.png")
    # 2) feed
    for k in range(posts_to_watch):
        info = await pg.evaluate("""()=>{const f=document.getElementById('feed');const its=[...f.querySelectorAll('.item')];
            const i=Math.round(f.scrollTop/f.clientHeight);const it=its[i]; if(!it) return null;
            const v=it.querySelector('video'); const t=(it.querySelector('h2,.title,h3')||{}).innerText||'';
            return {i, n:its.length, title:t.trim().slice(0,60), video:!!v, rs:v?v.readyState:null, ct:v?v.currentTime:null,
                    err:v&&v.error?v.error.code:null, dur:v?v.duration:null, sw:document.documentElement.scrollWidth}}""")
        if not info: log["actions"].append("nincs több poszt"); break
        log["seen"].append(info["title"])
        if info["sw"] > 392: log["layout"].append(f"vízszintes görgetés ({info['sw']}px) itt: {info['title']}")
        watch = r.uniform(tmin, tmax)
        await pg.wait_for_timeout(int(watch * 1000))
        if info["video"]:
            v2 = await pg.evaluate("""()=>{const f=document.getElementById('feed');const it=f.querySelectorAll('.item')[Math.round(f.scrollTop/f.clientHeight)];
                const v=it&&it.querySelector('video'); return v?{ct:v.currentTime,paused:v.paused,err:v.error?v.error.code:null,rs:v.readyState}:null}""")
            if v2 and (v2["err"] or (v2["ct"] < 0.5 and watch > 2)):
                log["video_issues"].append({"title": info["title"], **v2})
        item = pg.locator("#feed .item").nth(info["i"])
        async def act(label, sel):
            el = item.locator(sel)
            if await el.count():
                await el.first.click(); log["actions"].append(f"{label}: {info['title']}"); await pg.wait_for_timeout(500); return True
            return False
        if r.random() < ppoll:
            if await act("szavazás megnyitva", ".poll-toggle[data-a=poll]"):
                opts = item.locator("button.opt[data-a=vote]")
                n = await opts.count()
                if n:
                    pick = r.randrange(n)
                    await opts.nth(pick).click(); await pg.wait_for_timeout(600)
                    fb = await item.evaluate("(it)=>{const o=[...it.querySelectorAll('button.opt')];return o.map(x=>x.className)}")
                    log["actions"].append(f"szavazott ({pick+1}. opció) → {' '.join(c for c in fb if 'ok' in c or 'right' in c or 'good' in c)[:40] or 'visszajelzés ok'}")
        if r.random() < pdeep:
            if await act("Mélyebben", "button.deeper"):
                await pg.wait_for_timeout(int(r.uniform(1.5, 4) * 1000))
                await pg.screenshot(path=f"{outdir}/{name.split()[-1]}_melyebb.png")
                await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
                sb = pg.locator("#sheetBack")
                if await sb.count(): await sb.click(position={"x": 195, "y": 60})
        if r.random() < pc:
            if await act("komment megnyitva", 'button[aria-label="Kommentek"]'):
                ta = pg.locator("#cmText")
                if await ta.count() and await ta.is_enabled():
                    await ta.fill(ctext); await pg.locator("#cmSend").click(); await pg.wait_for_timeout(700)
                    shown = await pg.locator("#cmList").inner_text()
                    log["actions"].append("komment " + ("megjelent" if ctext[:15] in shown else "NEM jelent meg"))
                else:
                    log["actions"].append("komment mező tiltva")
                await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300)
        if r.random() < phab:
            await act("szokás vállalva", ".habit-toggle")
            await pg.keyboard.press("Escape")
        roll = r.random()
        if roll < pd:
            await act("Nem tetszik", 'button[aria-label^="Nem tetszik"]')
        elif roll < pd + pl:
            await act("Like", 'button[aria-label="Tetszik"]')
        await pg.evaluate("()=>{const f=document.getElementById('feed');f.scrollBy({top:f.clientHeight,behavior:'instant'})}")
        await pg.wait_for_timeout(900)
    await pg.screenshot(path=f"{outdir}/{name.split()[-1]}_2_vege.png")
    # 3) a többi fül
    for tab in ["Felfedezés", "Aréna", "Profil"]:
        t = pg.locator("nav button, .tabbar button, button").filter(has_text=tab)
        if await t.count():
            await t.first.click(); await pg.wait_for_timeout(1200)
            sw = await pg.evaluate("document.documentElement.scrollWidth")
            if sw > 392: log["layout"].append(f"vízszintes görgetés a(z) {tab} fülön ({sw}px)")
            await pg.screenshot(path=f"{outdir}/{name.split()[-1]}_3_{tab}.png")
            log["actions"].append(f"megnyitotta: {tab}")
    log["points_text"] = (await pg.evaluate("document.body.innerText.match(/(\\d+)\\s*pont/i)?.[0]||''"))
    log["seconds"] = round(time.time() - t0)
    await b.close()
    return log


async def main():
    names = random.sample(list(PANEL), 5)
    outdir = sys.argv[1]
    async with async_playwright() as pw:
        logs = await asyncio.gather(*[bot(pw, n, random.randint(7, 11), outdir) for n in names])
    json.dump(logs, open(f"{outdir}/eredmeny.json", "w"), ensure_ascii=False, indent=1)
    for L in logs:
        print(f"\n=== {L['name']} ({L['desc']}) – {L['seconds']} mp, {len(L['seen'])} poszt")
        print(" látta:", " | ".join(L["seen"]))
        print(" hibák:", L["errors"][:6] or "nincs")
        print(" videóhiba:", L["video_issues"] or "nincs", " elrendezés:", L["layout"] or "rendben")
        print(" tettek:", "; ".join(L["actions"]))
        print(" pont:", L["points_text"])

asyncio.run(main())
