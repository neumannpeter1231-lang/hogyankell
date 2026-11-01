# Hogyankell – munkafüzet (átadás új beszélgetéshez)

Utolsó frissítés: 2026-10-31 (este, 3. sorozat után). Ezt a fájlt az új Claude-beszélgetés elején kell elolvasni. Minden itt van, ami a folytatáshoz kell.

## Mi ez?
A **Hogyankell** Neumann Péter TikTok-szerű tanulóappja: rövid, rajzos magyarázóvideók gyakorlati élettudásról (meggyőzés, pszichológia, pénzügyek, idő és fókusz, kommunikáció, biztonság, alvás), szavazással, ellenőrző kérdésekkel, „Mélyebben” résszel (forrás), szokásvállalással, Arénával (párbaj, liga), kommentekkel.

## Hol van minden?
- **Élő app (zárt, meghívásos):** https://rough-sound-2c04.neumann-peter1231.workers.dev
- **Kód:** GitHub, privát: `neumannpeter1231-lang/hogyankell`. A `main` ágra pusholt változás kb. 1 perc alatt automatikusan élesedik (Cloudflare Worker „rough-sound-2c04”, a `site/` mappát szolgálja ki).
- **Adatbázis, belépés:** Supabase projekt `unzmjkzvkaqmumeqwsyf` (Google-belépés, meghívottak az `invites` táblában, adatok a `docs` táblában, RLS-szabályok a `supabase/*.sql` fájlokban).
- **Értesítések:** Supabase Edge Function `send-reminders` + pg_cron 5 percenként.
- **Hang:** ElevenLabs (Starter csomag), API-n. Hangok: Gábor `7B7mSWflzRSaO1yGeJH6`, Vera `xjlfQQ3ynqiEyRpArrT8`. Mellette Gemini TTS (`gemini-3.8-flash-tts`, ugyanaz a Gemini-kulcs és egyenleg): Charon, Orus, Fenrir (férfi), Kore, Aoede (női) – Péter választotta, a Sulafat kiesett.
- **Képek:** Gemini API, `gemini-nano-banana-2.1`, 9:16 – **teljesen automatikus** a `tools/kepek.py`-val (2026-10-31 óta; 5 $ előre feltöltve az AI Studióban). A régi böngészős ElevenLabs-módszer csak tartalék.

## A repó felépítése
- `prototipus/hogyankell.html` – az egész app egy fájlban (ezt kell szerkeszteni).
- `build.py` – a prototípusból elkészíti a `site/` mappát (ezt szolgálja ki a Cloudflare). Mindig: szerkesztés → `python3 build.py` → commit → push.
- `webapp/` – a webes burok: `backend.js` (Supabase-adapter, belépés, meghívás-ellenőrzés), service worker, manifest, adatvédelem.
- `tools/hang.py` – felolvasás ElevenLabs API-val, betűszintű időzítéssel → `anyag/<id>/hang.mp3` + `align.json`.
- `tools/osszerak.py` – videó összevágása: `anyag/<id>/01.png…` + hang → `media/<id>.mp4` (Ken Burns mozgás, pontos feliratok).
- `tools/posztok.py` – a sorozat-JSON alapján beszúrja a posztokat az appba (szavazás, ellenőrző kérdés, Mélyebben, forrás, szokás).
- `tools/szoveghang.py` – felolvasás a szöveges (nem videós) posztokhoz.
- `tools/kepek.py` – jelenetképek a Gemini API-ból (prompt + a sorozat `style` mezője) → `anyag/<id>/01.png…`; a meglévőket kihagyja.
- `anyag/sorozat1.json`, `anyag/sorozat2.json` – a forgatókönyvek (jelenetszöveg + képleírás + kérdések + forrás).
- `.secrets.env` – API-kulcsok, **gitből kizárva, nincs a GitHubon**. Új munkakörnyezetben Péternek újra meg kell adnia (ElevenLabs `sk_…` kulcs, Gemini kulcs).

## Új videósorozat menete
1. Forgatókönyv `anyag/sorozatN.json`-ba: 6 jelenet, 25–35 mp, valódi kutatás + forrás, a végén „így véded magad” tipp, néhány „tévhit vs. valóság” formátumban. Számokat ellenőrizni / kiszámolni.
2. `python3 tools/hang.py anyag/sorozatN.json`
3. `python3 tools/kepek.py anyag/sorozatN.json` (automatikus; utána kontaktlappal átnézni: nincs-e szöveg, valódi személy, márka a képen).
4. `python3 tools/osszerak.py anyag/sorozatN.json` → `python3 tools/posztok.py anyag/sorozatN.json` → ORDER-listába nem kötelező felvenni (a feed amúgy is keveri).
5. `python3 build.py`, commit, push, ellenőrzés élesben.

## Péter döntései (ezekhez tartsd magad)
- Mindig **magyarul** válaszolj.
- **Hang (2026-10-31-től):** minden videóban más hang szóljon, két egymást követőben soha ne ugyanaz. Profilok a `"hang"` mezőben: `gabor`, `vera_tanito`, `vera_kozepes`, `vera_elenk` (ElevenLabs), `gemini_charon`, `gemini_orus`, `gemini_fenrir`, `gemini_kore`, `gemini_aoede`. A 3. sorozat kiosztása: Charon, Vera, Kore, Gábor, Aoede, Orus → a 4. sorozat Fenrirrel kezd. Tanító jelleg, ne gesztikuláljon túl. A Gemini-hangnál a modell MINDEN szöveges előtagot (stílusutasítást) felolvas, ezért csak a sima szöveget kapja; jelenetenként külön olvas, az időzítést a hang.py becsüli a jeleneten belül.
- **Hang mindig szól**, a feedben nincs némító és nincs megállító gomb; koppintásra áll meg / indul.
- **Kommentek** a Mentés helyén. **Nem tetszik** gomb (Profilban visszahozható).
- **Feed keverve** minden megnyitáskor (nem látott elöl, témák váltakoznak).
- **Címek = a videó lényege** (pl. „Horgonyhatás”, „Szűkösség elve”).
- **Munkamódszer:** a 26 fős AI-tesztelőpanel (6 + 20 célcsoport-persona) szavaz minden javaslatra; ebben a sorrendben haladunk. Új javaslatot mindig az egész panellel kell szavaztatni. (Ez szimuláció, nem valódi emberek – ezt mindig jelezni kell.)
- Teljesen automatikus gyártást szeretne (API), nem gépéhez kötött megoldást.
- Minden válasz végén **„Péter teendői”** lista: amit Claude nem tehet meg (fizetés, éles adatbázis-módosítás Run gombja, letöltés).

## A panel szavazási sorrendje (a következő teendők alapja)
1. ✅ Pénzügyek téma (6 videó kész) · 2. ✅ +pont konfettivel · 3. **Csalások felismerése** (következő sorozat) · 4. ✅ Rövidebb videók · 5. ✅ „Így védd magad” rész · 6. Néma mód a Profilban (Péter eddig a mindig szóló hangot kérte – egyeztetni) · 7. ✅ részben Tévhit-formátum · 8. ✅ Sorozatszámláló · 9. Egyszerűbb szavak · 10. Munkahely (interjú, tárgyalás, munkajog) · 11. Egészség és alvás · 12. ✅ Rezgés · 13. Önbizalom és első benyomás · 14. Kapcsolatok · 15. Barát meghívása a ligába · 16. Pörgő pontszám · 17. Nagyobb betűs mód · 18. Gyerek és család · 19. Kommentmoderálás · 20. Viselkedési közgazdaságtan · 21. „Megelőzted X-et” · 22. Csak hang mód · 23. Egyszerű mód · 24. Borravaló-pszichológia

## Tartalom most (élesben)
- 23 AI-videó: Horgonyhatás, Szűkösség elve, Láb az ajtóban, Társas bizonyíték, Pratfall-hatás, Azonosítható áldozat hatás, Választási bénulás, Rím mint érv, A visszakérdezés ereje, Tekintély elve, Előfeszítés, Kamatos kamat, A fizetés fájdalma, A minimum törlesztés horgonya, Fizesd ki először magad, Infláció, Mentális könyvelés; 3. sorozat (a könyv „Védekezz” részeiből): Elsüllyedt költség, Csalimadár, Veszteségkerülés, Keretezés, Holdudvarhatás, Csúcs-vég szabály. **Új videó előtt ezt a listát ellenőrizni, téma nem ismétlődhet.**
- 8 podcastrészlet-videó + 7 felolvasott szöveges poszt. Rejtve (duplikátum): p3, p4, p5, m1, m4 (Csalimadár-hatás szöveges poszt, a videó mellett).

## Nyitott pontok
- ✅ **Kommentek Supabase-szabálya:** `supabase/4_kommentek.sql` lefutott (2026-10-31), Péter próbakommentet írt.
- ✅ **Teljesen automatikus képek:** 5 $ előre feltöltve (2026-10-31), a 3. sorozat (36 kép) után kb. 2,5 $ maradt. A Google Cloud 300 $-os próbakerete a Gemini API-ra NEM vonatkozik. Auto-reload kikapcsolva.
- **Meghívottak:** Mira (mira.hasznosi@gmail.com) meghívó-SQL-je beírva, Péter Run gombjára vár (2026-10-31).
- **ElevenLabs keret:** a 3. sorozat után kb. 1 100 karakter maradt november 30-ig (kb. 2 rövid narráció); addig főleg Gemini-hangok.
- **Valódi tesztelők:** 5–10 Gmail-cím kell az `invites` táblába; javasolt nézési statisztika (végignézés, elgörgetés, dislike) heti összefoglalóval.
- Ötletek a jövőre: ütemezett heti videógyártás, ha a képek is automatikusak.

## A 26 fős AI-tesztelőpanel (ugyanezekkel kell folytatni)
Első csapat (6): Lili 19 egyetemista, sokat TikTokozik · Bence 24 junior értékesítő · Kata 31 kisgyerekes anyuka · Tamás 45 kisvállalkozó, szkeptikus · Dóri 22 pszichológia szakos · Máté 20 gamer.
Második csapat (20): Erzsi 67 nyugdíjas · Gergő 38 középiskolai tanár · Nóra 29 ápoló · Zoli 41 kamionsofőr · Bianka 34 HR-es · Dávid 27 programozó · Réka 20 egyetemista · Ádám 36 kétgyerekes apa · Fanni 26 fodrász · Krisztián 30 startupalapító · Petra 28 ingatlanos · Bálint 21 közgáz hallgató · Lara 23 influenszer · Feri 50 biztonsági őr · Judit 44 könyvelő · Márk 25 edző · dr. Kovács Anna 40 pszichológus · Tibi 33 gyári műszakos · Dorina 22 pincér · Ilona 60 nagymama.
Eredmények: átlag 7,2 (1. csapat) és 7,0 (2. csapat); legjobban a munkájukhoz kötődő tartalmat értékelik, az idősebbek és a kevés idejűek a legkritikusabbak. Legkeresettebb téma: pénzügyek (26-ból 16), utána csalások, munkahely.

## Tartalmi szabályok
- Minden videó valódi, megnevezett kutatásra épül; a számokat ellenőrizd vagy számold ki; a „Mélyebben” részben a korlátokat is írd le (pl. megismétlési gondok).
- Pénzügyben nincs befektetési tanács; aktuális feltételeknél hivatalos forrásra utalj.
- Egyszerű, hétköznapi szavak (Tibi és Ilona kérése); 25–35 mp; 6 jelenet; a végén „A tipp: …”.
- A posztokon „AI-jal készült” jelölés van – maradjon.
- Valódi személyt ne rajzoltass felismerhetően (az Einstein-szerű figura határeset volt); márkát, logót, ismert rajzfilmfigurát ne.
- Forrás a meggyőzéses témákhoz: a tudástár projektben lévő „Meggyozestechnika_konyv_pontositott.docx” (Péter tanulójegyzete Újszászi Bogár László podcastjei alapján, kutatásokkal kiegészítve).

## Vizuális stílus
- App: sötét felület (#0E1116), sárga kiemelés (#F2C230), Inter Display betű, TikTok-szerű függőleges feed, jobb oldali gombsáv (Like, Nem tetszik, Komment, Küldés, Mélyebb).
- Képek: „bold flat cartoon, thick black outlines, vivid magenta, teal and yellow palette, retro comic, halftone dots, quirky characters with big round eyes, no text” (pontosan: sorozat-JSON `style` mező). Simpsons-szerű sárga figurák kerülendők.
- Videó: 720×1280, lassú zoom/úszás jelenetenként, nagy fehér felirat fekete körvonallal, alsó harmadban.

## Technikai buktatók (hogy ne kelljen újra kitalálni)
- iPhone: az első érintés előtt semmilyen weboldal nem adhat hangot – ezért a témaválasztó „Mehet” gombja oldja fel; visszatérőknek „Koppints, és indul a hang” felirat. A webes rezgést az iPhone nem támogatja.
- ElevenLabs képgenerálás automatizálása a böngészőben: a prompt mező `contenteditable`, `document.execCommand('insertText')`-tel tölthető; a Generate gomb `aria-label="Generate"`; beküldés után a History tetején ellenőrizd a prompt szövegét (különben duplán generál); a History lustán tölt (nem lát mindent a DOM).
- A letöltött képek neve: `ElevenLabs_image_google-nano-banana-2-1_<prompt első 15 karaktere>_<időbélyeg>.png`; az időbélyeg a KÉSZ idő, nem a beküldésé.
- A Supabase SQL-t Claude beírhatja (Monaco: `monaco.editor.getModels()[0].setValue(...)`), de a Run gombot Péternek kell megnyomnia.
- Az app `ORDER` és `HIDE` listája: a HIDE-ban lévő posztok nem jelennek meg; ami nincs az ORDER-ben, az is megjelenik (a feed keverve van).
- A szöveges posztok hangja: `VOICE` objektum az appban (a `media/hang/hang.json`-ből), újragenerálás: `tools/szoveghang.py`.
- `SOON_TOPICS` = a „hamarosan” témák (jelenleg Ügyintézés, Gyerek és család).

## Fiókok, költségek
- GitHub: neumannpeter1231-lang · Cloudflare: Worker „rough-sound-2c04” · Supabase: free tier · Google Cloud: „Hogyankell” projekt (OAuth + Gemini kulcs) · ElevenLabs: Starter.
- ElevenLabs keret megújul: **2026. november 30.** (Starter első hónap 1 $, utána 6 $/hó, kb. 39 000 kredit/hó). Egy 6 jelenetes videó kb. 1 000 kredit kép + 400–600 kredit hang.
- Google Gemini kép: kb. 0,067 $/kép (Nano Banana 2.1), előre feltöltéssel; Gemini TTS: pár cent videónként.
- Push-értesítés: a szerveroldal működik (cron 200 OK), Péter telefonján még nincs megerősítve, hogy megérkezett.
- Meghívott hozzáadása: Supabase → Table Editor → `invites` → új sor e-mail-címmel (vagy SQL: `insert into public.invites(email) values ('…');`).
