#!/bin/bash
# Bot-teszt helyben: az éles app-kód (site/) fut, a belépés és az adatbázis tesztváltozatra cserélve.
# Használat: bash tools/teszt/futtat.sh        (5 véletlen panel-persona + élő párbaj két böngészővel)
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd); W=$(mktemp -d)
cp -r "$ROOT/site" "$W/site" && cp "$ROOT/tools/teszt/teszt_backend.js" "$W/site/backend.js"
mkdir -p "$W/out"; cd "$W/site" && (python3 -m http.server 8765 >/dev/null 2>&1 &) && sleep 1
cd "$W" && python3 "$ROOT/tools/teszt/botok.py" "$W/out" && python3 "$ROOT/tools/teszt/elo_parbaj_teszt.py"
echo "Képernyőképek: $W/out"
