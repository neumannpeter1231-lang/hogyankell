#!/bin/bash
# Bot-teszt helyben: az éles app-kód (site/) fut, a belépés és az adatbázis tesztváltozatra cserélve.
# Használat: bash tools/teszt/futtat.sh        (5 véletlen panel-persona + élő párbaj két böngészővel + For You/témaszűrés/Adataim ellenőrzés)
# A böngészőt a CHROME_PATH változóval lehet megadni (alapból /usr/bin/google-chrome; CHROME_PATH="" → a Playwright saját Chromiuma).
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd); W=$(mktemp -d)
# Egy korábbi, beragadt teszt-szerver a 8765-ös porton a RÉGI buildet szolgálná ki (2026-11-03-án ez hamis
# eredményt adott), ezért indulás előtt leállítjuk, és a végén a sajátunkat is.
for p in $(ps -eo pid,args | awk '$2 ~ /python3?$/ && $3=="-m" && $4=="http.server" && $5=="8765" {print $1}'); do kill "$p" 2>/dev/null || true; done
cp -r "$ROOT/site" "$W/site" && cp "$ROOT/tools/teszt/teszt_backend.js" "$W/site/backend.js"
mkdir -p "$W/out"
python3 -m http.server 8765 --directory "$W/site" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
for i in $(seq 1 20); do curl -fs -o /dev/null http://127.0.0.1:8765/ && break; sleep 0.5; done
# külön sorokban, hogy a set -e bármelyik hibánál megálljon (egy &&-lánc elnyelné a hibakódot)
cd "$W"
python3 "$ROOT/tools/teszt/botok.py" "$W/out"
python3 "$ROOT/tools/teszt/elo_parbaj_teszt.py"
python3 "$ROOT/tools/teszt/foryou_teszt.py"
echo "Képernyőképek: $W/out"
