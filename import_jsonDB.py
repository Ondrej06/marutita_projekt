"""
import_jsonDB.py
================
Skript pro ruční import záložních statistik z game_stats.json do databáze.

Použití:
    python import_jsonDB.py

Kdy spustit:
    - Hráli jste bez běžícího Flask serveru → statistiky se uložily do game_stats.json.
    - Server je nyní spuštěn a chcete záznamy přesunout do databáze.
    - Záznamy bez user_id nebo username jsou přeskočeny (nelze je přiřadit uživateli).

Skript komunikuje se serverem přes REST API endpoint /api/update_stats,
takže Flask musí být spuštěn před spuštěním tohoto skriptu.
"""

import json
import os
import requests
import time

# URL Flask API endpointu pro uložení statistik
API_URL = "http://127.0.0.1:5000/api/update_stats"


def parse_json_objects(text: str) -> list:
    """
    Parsuje více JSON objektů z jednoho textového souboru.

    game_stats.json ukládá JSON objekty postupně za sebou (append),
    takže soubor obsahuje více kořenových objektů — standardní
    json.load() by selhal. Tato funkce je parsuje ručně.

    Algoritmus:
      - Prochází text znak po znaku a počítá hloubku složených závorek.
      - Při depth=0 a nalezení '}' je jeden objekt kompletní.
      - Znaky uvnitř řetězců se ignorují (detekce uvozovek a escape).

    Args:
        text: Celý obsah souboru game_stats.json jako řetězec.

    Returns:
        list: Seznam parsovaných Python slovníků (JSON objektů).
    """
    objects = []
    brace_count = 0   # Aktuální hloubka zanořování složených závorek
    start = 0         # Index začátku aktuálního JSON objektu
    in_string = False # True = jsme uvnitř JSON řetězce (ignorujeme závorky)
    escape = False    # True = následující znak je escapovaný (po zpětném lomítku)

    for i, ch in enumerate(text):
        # Přepínání stavu "jsme v řetězci" při neeescapovaných uvozovkách
        if ch == '"' and not escape:
            in_string = not in_string

        if not in_string:
            if ch == '{':
                if brace_count == 0:
                    start = i       # Začátek nového JSON objektu
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Celý objekt je kompletní — pokus o parsování
                    obj_str = text[start:i + 1]
                    try:
                        obj = json.loads(obj_str)
                        objects.append(obj)
                    except json.JSONDecodeError as e:
                        print(f"Chyba parsování objektu: {e}")

        # Správa escape stavu (\\ = literální zpětné lomítko, ne escape)
        if ch == '\\' and not escape:
            escape = True
        else:
            escape = False

    return objects


def import_json_to_db(json_file: str = "game_stats.json") -> None:
    """
    Načte záložní JSON soubor a odešle každý validní záznam na Flask API.

    Validní záznam musí obsahovat user_id a username — bez nich nelze
    statistiku přiřadit konkrétnímu uživateli v databázi.

    Po úspěšném importu se soubor přejmenuje na game_stats.json.imported,
    aby opakované spuštění skriptu nevytvářelo duplicity v databázi.

    Mezi každým požadavkem je 100ms pauza, aby server nebyl zahlcen.

    Args:
        json_file: Cesta k souboru se záložními statistikami.
    """
    # Kontrola, zda soubor nebyl již naimportován
    imported_file = json_file + ".imported"
    if not os.path.exists(json_file):
        if os.path.exists(imported_file):
            print(f"Soubor již byl naimportován ({imported_file}). Přeskakuji.")
        else:
            print(f"Soubor {json_file} nenalezen.")
        return

    # Načtení souboru
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Chyba při čtení souboru: {e}")
        return

    # Parsování všech JSON objektů ze souboru
    objects = parse_json_objects(content)
    print(f"Nalezeno {len(objects)} záznamů.")

    ok_count   = 0
    skip_count = 0

    for obj in objects:
        # Přeskoč záznamy bez identifikace uživatele
        if "user_id" not in obj or "username" not in obj:
            print(f"Přeskakuji záznam bez user_id/username: {obj}")
            skip_count += 1
            continue

        # Sestavení payload pro API endpoint
        payload = {
            "user_id":           obj["user_id"],
            "enemies_killed":    obj.get("enemies_killed", 0),
            "player_collisions": obj.get("player_collisions", 0),
            "projectiles_fired": obj.get("projectiles_fired", 0),
            "projectiles_hit":   obj.get("projectiles_hit", 0),
            "time_played":       obj.get("time_played", 0)  # Starší záznamy nemají time_played
        }

        # Odeslání na server
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"✓ OK: user_id {obj['user_id']} ({obj.get('username')})")
                ok_count += 1
            else:
                print(f"✗ Chyba {response.status_code}: {response.text}")
        except Exception as e:
            print(f"✗ Výjimka: {e}")

        # Krátká pauza mezi požadavky — předchází zahlcení serveru
        time.sleep(0.1)

    print(f"\nHotovo: {ok_count} importováno, {skip_count} přeskočeno.")

    # Přejmenování souboru — zabrání duplicitám při opakovaném spuštění
    if ok_count > 0:
        try:
            os.rename(json_file, imported_file)
            print(f"Soubor přejmenován na {imported_file}.")
        except Exception as e:
            print(f"Varování: soubor se nepodařilo přejmenovat: {e}")


if __name__ == "__main__":
    import_json_to_db()