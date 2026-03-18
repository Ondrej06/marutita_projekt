"""
path.py
=======
Centrální správa cest k souborům.

Všechny cesty jsou na jednom místě — při přejmenování nebo přesunu
souboru stačí změnit hodnotu zde, ostatní moduly to automaticky
převezmou bez nutnosti hledat výskyty napříč projektem.
"""


class Path:
    """Obsahuje cesty ke všem externím souborům projektu."""

    # Obrázek pozadí herní plochy (načítá se v PlayingState a game.py)
    background = "Assets\\back_1.png"

    # Záložní JSON soubor pro ukládání statistik, když Flask server neběží.
    # Při příštím startu serveru se data automaticky importují do databáze.
    json_save = "game_stats.json"