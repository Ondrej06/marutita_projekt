"""
settings.py
===========
Načítání a ukládání uživatelského nastavení aplikace.

Nastavení je persistentně uloženo v souboru config.json ve stejné
složce jako aplikace. Při každém spuštění se načte, při změně uloží.
Pokud soubor neexistuje nebo je poškozený, použijí se výchozí hodnoty.
"""

import json
import os

# Název konfiguračního souboru (relativní cesta ke spouštěcímu skriptu)
CONFIG_FILE = "config.json"

# Výchozí hodnoty konfigurace — použijí se při prvním spuštění nebo při chybě
DEFAULT_CONFIG = {
    "resolution": [1920, 1080],  # Rozlišení okna [šířka, výška] v pixelech
    "fullscreen": False,          # Celoobrazovkový režim (zatím nevyužito)
    "last_user": None,            # Uživatelské jméno naposledy přihlášeného uživatele
                                  # — předvyplní se v LoginState pro rychlejší přihlášení
}


def load_config() -> dict:
    """
    Načte konfiguraci ze souboru config.json.

    Pokud soubor existuje a je validní JSON, načte ho a doplní případné
    chybějící klíče výchozími hodnotami (zpětná kompatibilita).
    Pokud soubor neexistuje nebo je poškozený, vrátí DEFAULT_CONFIG.

    Returns:
        dict: Konfigurační slovník s klíči 'resolution', 'fullscreen', 'last_user'.
    """
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Doplní chybějící klíče výchozími hodnotami
                # — zajišťuje zpětnou kompatibilitu při přidání nových nastavení
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except Exception:
            # Poškozený nebo neparsovatelný JSON — vrátíme výchozí nastavení
            return DEFAULT_CONFIG.copy()
    else:
        # Soubor ještě neexistuje (první spuštění)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """
    Uloží konfiguraci do souboru config.json.

    Soubor se přepíše celý při každém volání.
    Odsazení (indent=4) zajišťuje čitelnost souboru pro uživatele.

    Args:
        config: Konfigurační slovník k uložení.
    """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)