# Hogyankell

Gyakorlati tudás rövid videókban – zárt tesztverzió.

- Élő oldal: https://rough-sound-2c04.neumann-peter1231.workers.dev
- `prototipus/hogyankell.html` – maga az app (ugyanez fut a claude.ai-os prototípusban)
- `webapp/` – belépés, adatbázis-kapcsolat, értesítések, telepíthető app
- `supabase/` – adatbázis (SQL) és az emlékeztetőket küldő függvény
- `build.py` – ebből készül a `site/` mappa; a Cloudflare a `main` ág minden frissítésekor ezt teszi ki

Titkos kulcs nem kerül ide (a `.gitignore` kizárja).
