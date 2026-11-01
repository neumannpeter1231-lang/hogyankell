import asyncio, json, os, sys
from playwright.async_api import async_playwright
BASE="http://127.0.0.1:8765/"
rooms={}  # code -> {uid: (page, name)}
log=[]
async def peers(code):
    ps=[{"id":u,"name":n} for u,(pg,n) in rooms.get(code,{}).items()]
    for u,(pg,n) in list(rooms.get(code,{}).items()):
        try: await pg.evaluate("ps=>window.__livePeersCb&&window.__livePeersCb(ps)", ps)
        except Exception: pass
def binder(pg):
    async def join(src, code, uid, name):
        rooms.setdefault(code,{})[uid]=(pg,name); asyncio.ensure_future(peers(code))
    async def send(src, code, uid, m):
        log.append((uid, m.get("t"), m.get("i")))
        for u,(p2,n) in list(rooms.get(code,{}).items()):
            if u!=uid: asyncio.ensure_future(p2.evaluate("m=>window.__liveRecv&&window.__liveRecv(m)", m))
    async def leave(src, code, uid):
        rooms.get(code,{}).pop(uid,None); asyncio.ensure_future(peers(code))
    return join, send, leave
async def newpage(b, bot):
    ctx=await b.new_context(viewport={"width":390,"height":844},is_mobile=True,has_touch=True,device_scale_factor=2)
    pg=await ctx.new_page(); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)[:200]))
    j,s,l=binder(pg)
    await pg.expose_binding("__liveJoin",j); await pg.expose_binding("__liveSend",s); await pg.expose_binding("__liveLeave",l)
    await pg.goto(BASE+"?bot="+bot); await pg.wait_for_timeout(1000)
    await pg.locator("#onbAll").click(); await pg.wait_for_timeout(600)
    for _ in range(9):   # pár videó „megnézése”, hogy legyen miből kérdezni
        await pg.evaluate("()=>{const f=document.getElementById('feed');f.scrollBy({top:f.clientHeight,behavior:'instant'})}"); await pg.wait_for_timeout(450)
    await pg.locator("nav.nav a[data-v=arena]").click(); await pg.wait_for_timeout(700)
    return pg, errs
async def txt(pg, sel):
    loc=pg.locator(sel)
    return (await loc.first.inner_text()).strip() if await loc.count() else None
async def main():
    res={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--mute-audio"])
        host,he=await newpage(b,"Peter"); guest,ge=await newpage(b,"Mira")
        # 1) házigazda: kód, és NEM indul el, amíg a másik nincs bent
        await host.locator("#friendDuel").click(); await host.wait_for_timeout(1500)
        code=await txt(host,"#duelPlay .code"); res["kód"]=code
        await host.wait_for_timeout(3000)
        res["vár amíg nincs bent (nincs kérdés)"]= (await host.locator("#dOpts").count())==0
        await host.screenshot(path=os.environ.get("OUT","out")+"/live_1_var.png")
        # 2) vendég beírja a kódot
        await guest.locator("#joinCode").fill(code); await guest.locator("#joinForm button[type=submit]").click()
        await guest.wait_for_timeout(1500)
        await guest.screenshot(path=os.environ.get("OUT","out")+"/live_2_visszaszamlal.png")
        await host.wait_for_selector("#dOpts", timeout=8000); await guest.wait_for_selector("#dOpts", timeout=8000)
        res["mindkettőnél ugyanaz az 1. kérdés"]= (await txt(host,"#duelPlay h2"))==(await txt(guest,"#duelPlay h2"))
        res["idő"]= await txt(host,"#tSec")
        await host.screenshot(path=os.environ.get("OUT","out")+"/live_3_kerdes.png")
        rounds=[]
        for qi in range(5):
            await host.wait_for_function(f"()=>document.querySelector('#duelPlay .eyebrow')&&document.querySelector('#duelPlay .eyebrow').innerText.includes('{qi+1}/')", timeout=40000)
            await guest.wait_for_function(f"()=>document.querySelector('#duelPlay .eyebrow')&&document.querySelector('#duelPlay .eyebrow').innerText.includes('{qi+1}/')", timeout=40000)
            same=(await txt(host,"#duelPlay h2"))==(await txt(guest,"#duelPlay h2"))
            await host.locator("#dOpts .dopt").nth(qi%3).click()
            await guest.wait_for_timeout(600)
            g_sees=await txt(guest,"#sOpp"); h_score=await txt(host,"#sMe")
            if qi==2:   # a vendég most nem válaszol: lejár a 20 mp
                await guest.wait_for_timeout(21500)
            else:
                await guest.wait_for_timeout(1500); await guest.locator("#dOpts .dopt").nth((qi+1)%3).click()
            await host.wait_for_timeout(700)
            h_sees=await txt(host,"#sOpp"); g_score=await txt(guest,"#sMe")
            rounds.append({"kérdés":qi+1,"azonos":same,"host pont":h_score,"vendég ezt látja a hostról":g_sees,"vendég pont":g_score,"host ezt látja a vendégről":h_sees})
            if qi==1: await host.screenshot(path=os.environ.get("OUT","out")+"/live_4_elo_pont.png")
        res["körök"]=rounds
        try:
            await host.wait_for_function("()=>document.body.innerText.toLowerCase().includes('élő párbaj vége')", timeout=15000)
        except Exception:
            print("HOST:", (await host.locator('#duelPlay').inner_text())[:500]); print("GUEST:", (await guest.locator('#duelPlay').inner_text())[:500]); print("ERR", he, ge); print("LOG", log[-12:]); print(json.dumps(res,ensure_ascii=False)); raise
        await guest.wait_for_function("()=>document.body.innerText.toLowerCase().includes('élő párbaj vége')", timeout=15000)
        res["host vége"]=(await txt(host,"#duelPlay h2")); res["vendég vége"]=(await txt(guest,"#duelPlay h2"))
        await host.screenshot(path=os.environ.get("OUT","out")+"/live_5_vege_host.png"); await guest.screenshot(path="out/live_5_vege_vendeg.png")
        # 3) kilépés játék közben
        await host.locator("#lvAgain").click(); await host.wait_for_timeout(1200)
        code2=await txt(host,"#duelPlay .code")
        await guest.locator("#back").click(); await guest.wait_for_timeout(400)
        await guest.locator("#joinCode").fill(code2); await guest.locator("#joinForm button[type=submit]").click()
        await host.wait_for_selector("#dOpts", timeout=10000)
        await guest.locator("#duelQuit").click(); await host.wait_for_timeout(1500)
        res["ha a haver kilép"]=await txt(host,"#duelPlay h2")
        # 4) nem létező kód: 5 mp után a régi kihívás-keresés üzenete
        await host.locator("#back").click(); await host.wait_for_timeout(300)
        await host.locator("#joinCode").fill("ZZZZZ"); await host.locator("#joinForm button[type=submit]").click()
        await host.wait_for_timeout(6500)
        res["rossz kód"]=await txt(host,"#friendNote")
        res["JS-hibák"]=he+ge
        await b.close()
    print(json.dumps(res,ensure_ascii=False,indent=1))
asyncio.run(main())
